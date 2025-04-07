#!/usr/bin/env python3
"""
Arquivo unificado do sistema prompt-tdd.
Combina as funcionalidades em um único ponto de entrada.
"""

import os
import sys
import json
import argparse
import subprocess
import uuid
from typing import Dict, Any
from dataclasses import dataclass
from pathlib import Path
from rich.console import Console

from src.core.agents import AgentOrchestrator
from src.core.models import ModelManager
from src.core.db import DatabaseManager
from src.core.logger import get_logger

# Configuração do logger
logger = get_logger(__name__)
console = Console()

# ----- Estruturas de dados compartilhadas -----

@dataclass
class Message:
    """Mensagem do protocolo MCP."""
    content: str
    metadata: Dict[str, Any] = None

@dataclass
class Response:
    """Resposta do protocolo MCP."""
    content: Any
    metadata: Dict[str, Any] = None

# ----- Funções utilitárias compartilhadas -----

def get_orchestrator() -> AgentOrchestrator:
    """
    Obtém uma instância configurada do orquestrador de agentes.
    
    Returns:
        AgentOrchestrator configurado
    """
    try:
        # Inicializa componentes
        model_manager = ModelManager()
        
        # Verifica se o modelo é o tinyllama e se está disponível
        if model_manager.model_name.startswith("tinyllama-") and not model_manager.tinyllama_model:
            logger.warning("Modelo TinyLlama não disponível. Iniciando com modelo OpenAI como fallback.")
            # Define o modelo para um modelo que não requer arquivo local
            os.environ["DEFAULT_MODEL"] = "gpt-3.5-turbo"
            # Reinicializa o model_manager com o novo modelo padrão
            model_manager = ModelManager()
            
        db = DatabaseManager()
        
        # Cria e configura orquestrador - apenas model_manager como parâmetro
        orchestrator = AgentOrchestrator(model_manager)
        # Define o db como atributo separado
        orchestrator.db = db
        
        logger.info(f"Orquestrador inicializado com sucesso usando modelo {model_manager.model_name}")
        return orchestrator
        
    except Exception as e:
        logger.error(f"Erro ao criar orquestrador: {str(e)}")
        raise

# ----- Funcionalidade CLI -----

def run_cli_mode(args):
    """
    Executa o sistema no modo CLI.
    
    Args:
        args: Argumentos da linha de comando
    
    Returns:
        Código de saída (0 para sucesso, 1 para erro)
    """
    try:
        # Imprime o cabeçalho
        print("🖥️ CLI do projeto prompt-tdd")
        
        # Executa o orquestrador
        orchestrator = get_orchestrator()
        result = orchestrator.execute(
            prompt=args.prompt, 
            format=args.format
        )
        
        # Formata a saída de acordo com o formato especificado
        if result.output:
            print("\n" + result.output)
            
        # Registra a execução no banco
        db = DatabaseManager()
        db.log_run(
            args.session_id if hasattr(args, 'session_id') else str(uuid.uuid4()),
            input=args.prompt,
            final_output=result.output,
            output_type=args.format
        )
            
        return 0
    except Exception as e:
        error_msg = str(e)
        logger.error(error_msg)
        print(error_msg, file=sys.stderr)
        return 1

# ----- Funcionalidade MCP -----

class MCPHandler:
    """Manipulador do protocolo MCP."""
    
    def __init__(self):
        """Inicializa o manipulador MCP."""
        self.model_manager = ModelManager()
        self.db = DatabaseManager()
        # Cria e configura orquestrador - apenas model_manager como parâmetro
        self.orchestrator = AgentOrchestrator(self.model_manager)
        # Define o db como atributo separado
        self.orchestrator.db = self.db
        logger.info("MCPHandler inicializado")
        
    def process_message(self, message: Message) -> Response:
        """
        Processa uma mensagem MCP.
        
        Args:
            message: Mensagem a ser processada
            
        Returns:
            Resposta processada
        """
        try:
            # Executa o orquestrador
            result = self.orchestrator.execute(
                prompt=message.content,
                format=message.metadata.get("format", "json")
            )
            
            return Response(
                content=result.output,
                metadata={
                    "status": "success",
                    "items": len(result.items),
                    "guardrails": len(result.guardrails),
                    "raw_responses": len(result.raw_responses)
                }
            )
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {str(e)}")
            return Response(
                content={"error": str(e)},
                metadata={"status": "error"}
            )
            
    def handle_message(self, message: Message) -> None:
        """
        Manipula uma mensagem MCP.
        
        Args:
            message: Mensagem a ser manipulada
        """
        try:
            # Processa a mensagem
            response = self.process_message(message)
            
            # Salva resposta no arquivo de saída
            output_file = "logs/mcp_output.log"
            with open(output_file, "w") as f:
                json.dump({
                    "content": response.content,
                    "metadata": response.metadata
                }, f, indent=2)
                
            logger.info(f"Resposta salva em: {output_file}")
            
        except Exception as e:
            logger.error(f"Erro ao manipular mensagem: {str(e)}")
            
            # Salva erro no arquivo de saída
            output_file = "logs/mcp_output.log"
            with open(output_file, "w") as f:
                json.dump({
                    "content": {"error": str(e)},
                    "metadata": {"status": "error"}
                }, f, indent=2)

    def run(self):
        """Executa o manipulador MCP."""
        try:
            # Lê o arquivo de pipe
            pipe_file = "logs/mcp_pipe.log"
            logger.info(f"Iniciando leitura do arquivo: {pipe_file}")
            
            with open(pipe_file, "r") as f:
                content = f.read().strip()
                
            if not content:
                logger.warning("Arquivo vazio")
                return
                
            # Processa o conteúdo
            try:
                message_data = json.loads(content)
                message = Message(
                    content=message_data["content"],
                    metadata=message_data.get("metadata", {})
                )
            except json.JSONDecodeError:
                message = Message(content=content, metadata={})
            
            # Processa a mensagem
            self.handle_message(message)
            
            # Remove o arquivo após processamento
            os.remove(pipe_file)
            logger.info("Arquivo removido")
            
        except Exception as e:
            logger.error(f"Erro ao executar MCP: {str(e)}")
            raise

def run_mcp_mode():
    """Executa o sistema no modo MCP."""
    handler = MCPHandler()
    handler.run()

def check_model_availability():
    """
    Verifica se o modelo TinyLlama está disponível e tenta baixá-lo se necessário.
    """
    try:
        # Verifica a variável de ambiente para determinar se deve usar modelo local
        use_local_model = os.environ.get("USE_LOCAL_MODEL", "true").lower() == "true"
        if not use_local_model:
            logger.info("Configurado para não usar modelo local, pulando verificação de disponibilidade")
            return
            
        # Verifica se o arquivo do modelo existe
        base_dir = Path(__file__).resolve().parent.parent
        model_path = os.path.join(base_dir, "models", "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf")
        
        if not os.path.exists(model_path) or os.path.getsize(model_path) < 1000000:  # Menos de 1MB
            logger.warning(f"Modelo TinyLlama não encontrado ou incompleto em: {model_path}")
            logger.info("Tentando baixar o modelo usando 'make download-model'...")
            
            # Executa o comando make para baixar o modelo
            result = subprocess.run(["make", "download-model"], 
                                   cwd=base_dir,
                                   capture_output=True, 
                                   text=True)
            
            if result.returncode == 0:
                logger.info("Modelo baixado com sucesso!")
            else:
                logger.warning(f"Falha ao baixar o modelo: {result.stderr}")
                logger.warning("O sistema usará um modelo de fallback.")
        else:
            logger.info(f"Modelo TinyLlama encontrado: {model_path}")
            
    except Exception as e:
        logger.warning(f"Erro ao verificar/baixar modelo: {str(e)}")
        logger.warning("O sistema usará um modelo de fallback.")

# ----- Função principal -----

def main():
    """Função principal que unifica todas as entradas."""
    # Verifica a disponibilidade do modelo
    check_model_availability()
    
    parser = argparse.ArgumentParser(description="Prompt TDD - Sistema unificado")
    subparsers = parser.add_subparsers(dest="mode", help="Modo de execução")
    
    # Subparser para o modo app
    app_parser = subparsers.add_parser("app", help="Executa no modo aplicação")
    
    # Subparser para o modo cli
    cli_parser = subparsers.add_parser("cli", help="Executa no modo CLI")
    cli_parser.add_argument("prompt", help="Prompt para o agente")
    cli_parser.add_argument("--format", default="json", choices=["json", "markdown", "text"], 
                           help="Formato de saída")
    cli_parser.add_argument("--session-id", default="cli", help="ID da sessão")
    
    # Subparser para o modo mcp
    mcp_parser = subparsers.add_parser("mcp", help="Executa no modo MCP")
    
    args = parser.parse_args()
    
    # Se nenhum modo for especificado, usa o modo cli por padrão
    if not args.mode:
        parser.print_help()
        return 1
    
    # Executa o modo selecionado
    if args.mode == "app":
        run_app_mode()
        return 0
    elif args.mode == "cli":
        return run_cli_mode(args)
    elif args.mode == "mcp":
        run_mcp_mode()
        return 0
    
    return 0

if __name__ == "__main__":
    sys.exit(main())