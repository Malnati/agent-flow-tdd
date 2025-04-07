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

    def __init__(self):
        """Inicializa o orquestrador."""
        self.models = ModelManager()
        self.db = DatabaseManager()
        self.input_guardrail = InputGuardrail(self.models)
        self.output_guardrail = OutputGuardrail(self.models)
        logger.info("AgentOrchestrator inicializado")

    def execute(self, prompt: str, **kwargs) -> AgentResult:
        """
        Executa o processamento do prompt.
        
        Args:
            prompt: Texto de entrada
            **kwargs: Argumentos adicionais
            
        Returns:
            AgentResult com o resultado do processamento
        """
        try:
            logger.info(f"INÍCIO - execute | Prompt: {prompt[:CONFIG['logging']['truncate_length']]}...")
            
            # Aplica guardrail de entrada
            input_result = self.input_guardrail.process(prompt)
            
            # Configura o modelo
            self.models.configure(
                model=kwargs.get("model", CONFIG["model"]["name"]),
                temperature=kwargs.get("temperature", CONFIG["model"]["temperature"])
            )
            
            # Usa o prompt estruturado se o guardrail foi bem sucedido
            final_prompt = input_result.get("prompt", prompt) if input_result["status"] == "success" else prompt
            
            # Gera resposta
            text = self.models.generate_response([
                {"role": "system", "content": "Você é um assistente especializado em análise de requisitos."},
                {"role": "user", "content": final_prompt}
            ])
            
            # Aplica guardrail de saída
            output_result = self.output_guardrail.process(text, final_prompt)
            
            # Se o guardrail de saída encontrou campos ausentes, usa a saída melhorada
            if output_result["status"] == "success":
                text = output_result["output"]
            
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
