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
from src.core.model_manager import ModelManager
from src.core.logger import setup_logger
from src.core.utils import get_env_var, get_env_status as get_utils_env_status

app = typer.Typer()
output_console = Console()  # Console para saída normal
logger = setup_logger(__name__)

def validate_env() -> None:
    """
    Valida variáveis de ambiente necessárias.
    
    Raises:
        typer.Exit: Se alguma variável obrigatória não estiver definida
    """
    status = get_utils_env_status()
    if not status["all_required_set"]:
        missing = [var for var, set_ in status["required"].items() if not set_]
        error_msg = f"Variáveis de ambiente obrigatórias não definidas: {', '.join(missing)}"
        logger.error(error_msg)
        print(error_msg, file=sys.stderr)
        raise typer.Exit(code=1)

def get_env_status() -> dict:
    """
    Retorna status das variáveis de ambiente.
    
    Returns:
        Dict com status das variáveis obrigatórias e opcionais
    """
    return get_utils_env_status()

def get_orchestrator() -> AgentOrchestrator:
    """
    Retorna uma instância do AgentOrchestrator.
    
    Returns:
        AgentOrchestrator: Nova instância do orquestrador
    """
    return AgentOrchestrator()

@app.command()
def status():
    """
    Exibe o status do ambiente e configurações.
    """
    try:
        # Obtém status do ambiente
        env_status = get_env_status()
        
        # Obtém modelos disponíveis
        model_manager = ModelManager()
        available_models = model_manager.get_available_models()
        
        # Formata saída
        status = {
            "environment": env_status,
            "models": available_models
        }
        
        output_console.print(json.dumps(status, indent=2))
        return 0
        
    except Exception as e:
        error_msg = f"Erro ao processar comando: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(error_msg, file=sys.stderr)
        raise typer.Exit(code=1)

@app.command()
def mcp(
    prompt_tdd: str = typer.Argument(""),
    format: str = typer.Option("json", help="Formato de saída (json, markdown)"),
    model: str = typer.Option("gpt-3.5-turbo", help="Modelo a ser usado"),
    temperature: float = typer.Option(0.7, help="Temperatura para geração")
):
    """
    Executa o Agent Flow TDD em modo MCP.
    """
    try:
        print("🛠️ Executando CLI em modo desenvolvimento...")
        
        # Valida ambiente
        validate_env()
        
        from src.mcp import MCPHandler
        
        # Inicializa handler MCP
        handler = MCPHandler()
        handler.initialize(api_key=get_env_var("OPENAI_API_KEY"))
        
        # Executa loop MCP
        handler.run()
        return 0
        
    except Exception as e:
        error_msg = f"Erro ao processar comando: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(error_msg, file=sys.stderr)
        raise typer.Exit(code=1)

@app.command()
def feature(
    prompt_tdd: str = typer.Argument(..., help="Prompt para o TDD"),
    format: str = typer.Option("json", help="Formato de saída (json, markdown)"),
    model: str = typer.Option("gpt-3.5-turbo", help="Modelo a ser usado"),
    temperature: float = typer.Option(0.7, help="Temperatura para geração")
):
    """
    Executa o Agent Flow TDD para gerar uma feature.
    """
    try:
        print("🛠️ Executando CLI em modo desenvolvimento...")
        
        # Valida ambiente
        validate_env()
        
        # Inicializa orquestrador
        orchestrator = get_orchestrator()
        
        # Executa o prompt
        result = orchestrator.execute(
            prompt=prompt_tdd,
            model=model,
            temperature=temperature,
            session_id=str(time.time()),
            format=format
        )
        
        # Formata e exibe resultado
        if format == "markdown":
            output_console.print(Markdown(result.output))
        else:
            try:
                # Tenta carregar como JSON
                content = json.loads(result.output)
            except json.JSONDecodeError:
                # Se falhar, usa como string
                content = result.output
                
            output = {
                "content": content,
                "metadata": {
                    "type": "feature",
                    "options": {
                        "format": format,
                        "model": model,
                        "temperature": temperature
                    }
                }
            }
            print(json.dumps(output, ensure_ascii=False))
            
        return 0
        
    except Exception as e:
        error_msg = f"Erro ao processar comando: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(error_msg, file=sys.stderr)
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
