"""
CLI do Agent Flow TDD.
"""
import json
import sys
import time

import typer
from rich.console import Console
from rich.markdown import Markdown

from src.app import AgentOrchestrator
from src.core.logger import setup_logger

app = typer.Typer()
console = Console()
logger = setup_logger(__name__)

@app.command()
def main(
    prompt_tdd: str,
    mode: str = "mcp",
    format: str = "json",
    model: str = "gpt-3.5-turbo",
    temperature: float = 0.7,
):
    """
    Executa o Agent Flow TDD.
    
    Args:
        prompt_tdd: Prompt para o TDD
        mode: Modo de execução (mcp, cli)
        format: Formato de saída (json, markdown)
        model: Modelo a ser usado
        temperature: Temperatura para geração
    """
    try:
        console.print("🛠️ Executando CLI em modo desenvolvimento...")
        
        # Inicializa orquestrador
        orchestrator = AgentOrchestrator()
        
        # Executa o prompt
        result = orchestrator.execute(
            prompt=prompt_tdd,
            model=model,
            temperature=temperature,
            session_id=str(time.time())
        )
        
        # Formata e exibe resultado
        if format == "markdown":
            console.print(Markdown(result.output))
        else:
            output = {
                "content": result.output,
                "metadata": {
                    "type": "feature",
                    "options": {
                        "format": format,
                        "model": model,
                        "temperature": temperature
                    }
                }
            }
            print(json.dumps(output))
        
    except Exception as e:
        logger.error(f"FALHA - main | Erro: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    app()
