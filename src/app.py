"""
Orquestrador de agentes do sistema.
"""
from typing import Any, Dict, List
import yaml
import os
from pydantic import BaseModel

from src.core import ModelManager
from src.core.db import DatabaseManager
from src.core.logger import get_logger

logger = get_logger(__name__)

# Carrega configurações
def load_config() -> Dict[str, Any]:
    """Carrega configurações do arquivo YAML."""
    config_path = os.path.join(os.path.dirname(__file__), "configs", "cli.yaml")
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            return config["app"]  # Retorna apenas a seção 'app' do arquivo
    except Exception as e:
        logger.error(f"Erro ao carregar configurações: {str(e)}", exc_info=True)
        raise

# Configurações globais
CONFIG = load_config()

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
            
            # Configura o modelo
            self.models.configure(
                model=kwargs.get("model", CONFIG["model"]["name"]),
                temperature=kwargs.get("temperature", CONFIG["model"]["temperature"])
            )
            
            # Gera resposta
            text, metadata = self.models.generate(prompt)
            
            # Processa o resultado
            result = AgentResult(
                output=text,
                items=[],  # Implementar geração de itens
                guardrails=[],  # Implementar verificação de guardrails
                raw_responses=[{
                    CONFIG["database"]["metadata_id_field"]: metadata.get(CONFIG["database"]["metadata_id_field"]),
                    "response": metadata
                }]
            )
            
            # Registra no banco de dados
            run_id = self.db.log_run(
                session_id=kwargs.get("session_id", CONFIG["database"]["default_session"]),
                input=prompt,
                final_output=result.output,
                last_agent=CONFIG["database"]["default_agent"],
                output_type=kwargs.get("format", CONFIG["database"]["default_output_format"])
            )
            
            # Registra itens gerados
            for item in result.items:
                self.db.log_run_item(run_id, CONFIG["database"]["item_type"], item)
                
            # Registra guardrails
            for guardrail in result.guardrails:
                self.db.log_guardrail_results(run_id, CONFIG["database"]["guardrail_type"], guardrail)
                
            # Registra respostas brutas
            for response in result.raw_responses:
                self.db.log_raw_response(run_id, response)
            
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
