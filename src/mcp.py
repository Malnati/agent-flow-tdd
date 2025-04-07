#!/usr/bin/env python3
"""
Manipulador do protocolo MCP (Master Control Program).
"""
import os
import json
from typing import Dict, Any
from dataclasses import dataclass

from src.core.agents import AgentOrchestrator
from src.core.models import ModelManager
from src.core.db import DatabaseManager
from src.core.logger import get_logger

logger = get_logger(__name__)

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

class MCPHandler:
    """Manipulador do protocolo MCP."""
    
    def __init__(self):
        """Inicializa o manipulador MCP."""
        self.model_manager = ModelManager()
        self.db = DatabaseManager()
        self.orchestrator = AgentOrchestrator(self.model_manager, self.db)
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
                session_id=message.metadata.get("session_id", "mcp"),
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

if __name__ == "__main__":
    # Executar como serviço standalone
    handler = MCPHandler()
    handler.run()
