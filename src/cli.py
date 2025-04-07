#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Interface de linha de comando do sistema."""

import sys
import argparse
from rich.console import Console

from src.core.agents import AgentOrchestrator
from src.core.models import ModelManager
from src.core.db import DatabaseManager
from src.core.logger import get_logger

# Configuração do logger
logger = get_logger(__name__)
console = Console()

def get_orchestrator() -> AgentOrchestrator:
    """Obtém uma instância configurada do orquestrador de agentes."""
    model_manager = ModelManager()
    return AgentOrchestrator(model_manager)

def main():
    """Função principal do CLI."""
    parser = argparse.ArgumentParser(description="CLI do projeto prompt-tdd")
    parser.add_argument("prompt", help="Prompt para o agente")
    parser.add_argument("--format", default="json", choices=["json", "markdown"], help="Formato de saída")
    parser.add_argument("--mode", default="feature", choices=["feature", "docs"], help="Modo de operação")
    
    args = parser.parse_args()
    
    try:
        # Imprime o cabeçalho
        print("🖥️ CLI do projeto prompt-tdd")
        
        # Executa o orquestrador
        orchestrator = get_orchestrator()
        result = orchestrator.execute(args.prompt, args.format, args.mode)
        
        # Formata a saída de acordo com o formato especificado
        if result.output:
            print("\n" + result.output)
            
        # Registra a execução no banco
        db = DatabaseManager()
        db.log_run(
            prompt=args.prompt,
            output=result.output,
            output_type=args.format,
            format=args.format,
            raw_responses=result.raw_responses,
            guardrails=result.guardrails,
            items=result.items
        )
            
        return 0
    except Exception as e:
        error_msg = str(e)
        logger.error(error_msg)
        print(error_msg, file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
