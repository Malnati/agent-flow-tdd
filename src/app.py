"""
Orquestrador de agentes do sistema.
"""
from typing import Any, Dict, List, Optional
import yaml
import os
from pydantic import BaseModel

from src.core import ModelManager
from src.core.db import DatabaseManager
from src.core.logger import get_logger
from src.core.models import InputGuardrail, OutputGuardrail

logger = get_logger(__name__)

# Carrega configurações
def load_config() -> Dict[str, Any]:
    """Carrega configurações do arquivo YAML."""
    config_path = os.path.join(os.path.dirname(__file__), "configs", "cli.yaml")
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            return config["app"]
    except Exception as e:
        logger.error(f"Erro ao carregar configurações: {str(e)}", exc_info=True)
        raise

# Configurações globais
CONFIG = load_config()

class PromptRequirement(BaseModel):
    """Requisito para estruturação do prompt."""
    name: str
    description: str
    required: bool = True
    value: Optional[str] = None

class AgentResult(BaseModel):
    """Resultado de uma execução do agente."""
    output: Any
    items: List[Dict[str, Any]] = CONFIG["result"]["default_items"]
    guardrails: List[Dict[str, Any]] = CONFIG["result"]["default_guardrails"]
    raw_responses: List[Dict[str, Any]] = []

class AgentOrchestrator:
    """Orquestrador de agentes do sistema."""

    def __init__(self, model_manager: Optional[ModelManager] = None):
        """
        Inicializa o orquestrador.
        
        Args:
            model_manager: Gerenciador de modelos opcional
        """
        self.model_manager = model_manager or ModelManager()
        self.input_guardrail = InputGuardrail(self.model_manager)
        self.output_guardrail = OutputGuardrail(self.model_manager)
        self.db = DatabaseManager()
        logger.info("AgentOrchestrator inicializado")

    def execute(self, prompt: str, **kwargs) -> AgentResult:
        """
        Executa o fluxo do agente.
        
        Args:
            prompt: Prompt do usuário
            **kwargs: Argumentos adicionais
            
        Returns:
            Resultado da execução
        """
        try:
            # Processa o prompt com o guardrail de entrada
            input_result = self.input_guardrail.process(prompt)
            
            if input_result["status"] == "error":
                logger.error(f"FALHA - input_guardrail | {input_result['error']}")
                raise ValueError(input_result["error"])
                
            # Gera resposta com o modelo
            messages = [
                {"role": "system", "content": CONFIG["prompts"]["system"]},
                {"role": "user", "content": input_result["prompt"]}
            ]
            
            text = self.model_manager.generate_response(messages)
            
            # Processa a saída com o guardrail
            output_result = self.output_guardrail.process(text, input_result["prompt"])
            
            if output_result["status"] == "error":
                logger.error(f"FALHA - output_guardrail | {output_result['error']}")
                raise ValueError(output_result["error"])
                
            # Processa o resultado
            result = AgentResult(
                output=text,
                items=[],
                guardrails=[input_result, output_result],
                raw_responses=[]
            )
            
            # Registra no banco de dados
            run_id = self.db.log_run(
                session_id=kwargs.get("session_id", CONFIG["database"]["default_session"]),
                input=prompt,
                final_output=result.output,
                last_agent=CONFIG["database"]["default_agent"],
                output_type=kwargs.get("format", CONFIG["database"]["default_output_format"])
            )
            
            # Registra a resposta bruta
            self.db.log_raw_response(
                run_id=run_id,
                response={
                    "content": text,
                    "model": self.model_manager.model_name,
                    "provider": "tinyllama"
                }
            )
            
            # Registra guardrails
            self.db.log_guardrail_results(
                run_id=run_id,
                guardrail_type="input",
                results=input_result
            )
            self.db.log_guardrail_results(
                run_id=run_id,
                guardrail_type="output",
                results=output_result
            )
            
            logger.info(f"SUCESSO - execute | Tamanho da resposta: {len(result.output)}")
            return result
            
        except Exception as e:
            logger.error(f"FALHA - execute | Erro: {str(e)}", exc_info=True)
            raise
        finally:
            self.db.close()

# Uso
if __name__ == "__main__":
    orchestrator = AgentOrchestrator()
    user_prompt = CONFIG["example"]["prompt"]
    result = orchestrator.execute(user_prompt)
    print("Resultado Final:", result.output)
