"""
CLI para o sistema.
Módulo principal que define os comandos disponíveis na interface de linha de comando.
"""
import json
import sys
import time
import os
from typing import Dict

import typer
import yaml
from rich.console import Console
from rich.markdown import Markdown

from src.app import AgentOrchestrator
from src.core.models import ModelManager
from src.core.logger import get_logger, log_execution
from src.core.kernel import get_env_var, get_env_status as get_kernel_env_status, validate_env as validate_kernel_env

# Constantes do sistema
EXIT_CODE_SUCCESS = 0
EXIT_CODE_ERROR = 1
EMPTY_PROMPT = ""

def generate_session_id() -> str:
    """Gera um ID de sessão baseado no timestamp atual."""
    return str(time.time())

# Carrega configurações
def load_config() -> Dict:
    """Carrega configurações do arquivo YAML."""
    config_path = os.path.join(os.path.dirname(__file__), "configs", "cli.yaml")
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            # Mescla configurações de logging do app com o config principal
            config["logging"] = config["app"]["logging"]
            return config
    except Exception as e:
        logger.error(f"Erro ao carregar configurações: {str(e)}", exc_info=True)
        raise

# Configurações globais
CONFIG = load_config()

# Logger e Console
logger = get_logger(__name__)
app = typer.Typer()
output_console = Console()  # Console para saída normal

def get_env_status() -> Dict[str, Dict[str, bool]]:
    """
    Obtém o status das variáveis de ambiente.

    Returns:
        Dict com o status das variáveis.
    """
    return get_kernel_env_status("cli")

@log_execution
def validate_env() -> None:
    """
    Valida se todas as variáveis de ambiente obrigatórias estão definidas.

    Raises:
        ValueError: Se alguma variável obrigatória não estiver definida.
    """
    try:
        validate_kernel_env("cli")
    except ValueError as e:
        logger.error(str(e))
        print(str(e), file=sys.stderr)
        raise typer.Exit(code=EXIT_CODE_ERROR)

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
        models = ModelManager()
        available_models = models.get_available_models()
        
        # Formata saída
        status = {
            "environment": env_status,
            "models": available_models
        }
        
        output_console.print(json.dumps(status, indent=CONFIG["cli"]["json"]["indent"]))
        return EXIT_CODE_SUCCESS
        
    except Exception as e:
        error_msg = f"{CONFIG['cli']['messages']['error_prefix']}{str(e)}"
        logger.error(error_msg, exc_info=CONFIG["logging"]["error_show_traceback"])
        print(error_msg, file=sys.stderr)
        raise typer.Exit(code=EXIT_CODE_ERROR)

@app.command()
def mcp(
    prompt_tdd: str = typer.Argument(EMPTY_PROMPT),
    format: str = typer.Option(
        CONFIG["cli"]["output"]["default_format"],
        help=f"Formato de saída ({', '.join(CONFIG['cli']['output']['available_formats'])})"
    ),
    model: str = typer.Option(
        CONFIG["cli"]["model"]["default_name"],
        help="Modelo a ser usado"
    ),
    temperature: float = typer.Option(
        CONFIG["cli"]["model"]["default_temperature"],
        help="Temperatura para geração"
    )
):
    """
    Executa o Agent Flow TDD em modo MCP.
    """
    try:
        print(CONFIG["cli"]["messages"]["start_dev"])
        
        # Valida ambiente
        validate_env()
        
        from src.mcp import MCPHandler
        
        # Inicializa handler MCP
        handler = MCPHandler()
        handler.initialize(api_key=get_env_var("OPENAI_API_KEY"))
        
        # Executa loop MCP
        handler.run()
        return EXIT_CODE_SUCCESS
        
    except Exception as e:
        error_msg = f"{CONFIG['cli']['messages']['error_prefix']}{str(e)}"
        logger.error(error_msg, exc_info=CONFIG["logging"]["error_show_traceback"])
        print(error_msg, file=sys.stderr)
        raise typer.Exit(code=EXIT_CODE_ERROR)

@app.command()
def feature(
    prompt_tdd: str = typer.Argument(..., help="Prompt para o TDD"),
    format: str = typer.Option(
        CONFIG["cli"]["output"]["default_format"],
        help=f"Formato de saída ({', '.join(CONFIG['cli']['output']['available_formats'])})"
    ),
    model: str = typer.Option(
        CONFIG["cli"]["model"]["default_name"],
        help="Modelo a ser usado"
    ),
    temperature: float = typer.Option(
        CONFIG["cli"]["model"]["default_temperature"],
        help="Temperatura para geração"
    )
):
    """
    Executa o Agent Flow TDD para gerar uma feature.
    """
    try:
        print(CONFIG["cli"]["messages"]["start_dev"])
        
        # Valida ambiente
        validate_env()
        
        # Inicializa orquestrador
        orchestrator = get_orchestrator()
        
        # Executa o prompt
        result = orchestrator.execute(
            prompt=prompt_tdd,
            model=model,
            temperature=temperature,
            session_id=generate_session_id(),
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
                    "type": CONFIG["cli"]["json"]["metadata_type"],
                    "options": {
                        "format": format,
                        "model": model,
                        "temperature": temperature
                    }
                }
            }
            print(json.dumps(
                output,
                ensure_ascii=CONFIG["cli"]["json"]["ensure_ascii"],
                indent=CONFIG["cli"]["json"]["indent"]
            ))
            
        return EXIT_CODE_SUCCESS
        
    except Exception as e:
        error_msg = f"{CONFIG['cli']['messages']['error_prefix']}{str(e)}"
        logger.error(error_msg, exc_info=CONFIG["logging"]["error_show_traceback"])
        print(error_msg, file=sys.stderr)
        raise typer.Exit(code=EXIT_CODE_ERROR)

if __name__ == "__main__":
    app()
