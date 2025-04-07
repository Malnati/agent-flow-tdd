"""
Interface de linha de comando do sistema.
"""

import sys
import click
from rich.console import Console
from rich.table import Table
import os
from typing import Optional

from src.core import AgentOrchestrator, ModelManager, DatabaseManager
from src.core.kernel import get_env_var, validate_env, get_env_status, setup_paths
from src.core.logger import get_logger

logger = get_logger(__name__)
console = Console()

def get_orchestrator() -> AgentOrchestrator:
    """
    Obtém uma instância configurada do orquestrador de agentes.
    
    Returns:
        AgentOrchestrator configurado
    """
    try:
        # Inicializa componentes
        model_manager = ModelManager()
        db = DatabaseManager()
        
        # Cria e retorna orquestrador
        orchestrator = AgentOrchestrator(model_manager, db)
        logger.info("Orquestrador inicializado com sucesso")
        return orchestrator
        
    except Exception as e:
        logger.error(f"Erro ao criar orquestrador: {str(e)}")
        raise

@click.group()
def cli():
    """CLI do projeto prompt-tdd."""
    pass

@cli.command()
@click.argument("prompt")
@click.option("--format", default="text", help="Formato de saída (text/json/markdown)")
def feature(prompt: str, format: str):
    """
    Gera uma feature com base no prompt fornecido.
    
    Args:
        prompt: Descrição da feature
        format: Formato de saída
    """
    try:
        # Valida ambiente
        validate_env()
        
        # Obtém orquestrador
        orchestrator = get_orchestrator()
        
        # Executa o orquestrador
        result = orchestrator.execute(
            prompt=prompt,
            session_id="cli",
            format=format
        )
        
        # Imprime resultado
        print(result.output)
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Erro ao gerar feature: {str(e)}")
        print(f"❌ Erro: {str(e)}")
        sys.exit(1)

@cli.command()
@click.option("--prompt-tdd", required=True, help="Prompt para o TDD")
@click.option("--format", default="json", help="Formato de saída (json/markdown)")
def dev(prompt_tdd: str, format: str):
    """Executa o CLI em modo desenvolvimento."""
    try:
        # Valida ambiente
        validate_env("dev")
        
        # Inicializa componentes
        model = ModelManager("tinyllama-1.1b")
        db = DatabaseManager()
        orchestrator = AgentOrchestrator(model, db)
        
        # Executa
        result = orchestrator.execute(prompt_tdd, format)
        print(result.output)
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}", file=sys.stderr)
        sys.exit(1)

@cli.command()
def status():
    """Verifica status do ambiente."""
    try:
        # Valida ambiente
        validate_env("status")
        print("✅ Ambiente configurado corretamente")
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}", file=sys.stderr)
        sys.exit(1)

def app(args=None):
    """
    Função principal da CLI.
    
    Args:
        args: Lista de argumentos da linha de comando
    """
    try:
        # Configura caminhos
        setup_paths()
        
        # Executa CLI
        cli(args)
    except Exception as e:
        logger.error(f"Erro na CLI: {str(e)}")
        print(f"❌ Erro: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    app()
