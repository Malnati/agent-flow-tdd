"""
Orquestrador de agentes do sistema.
"""
from typing import Any, Dict, List
from pydantic import BaseModel

from src.core import ModelManager
from src.core.db import DatabaseManager
from src.core.logger import get_logger

logger = get_logger(__name__)


class AgentResult(BaseModel):
    """Resultado de uma execução do agente."""
    output: Any
    items: List[Dict[str, Any]] = []
    guardrails: List[Dict[str, Any]] = []
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
            logger.info(f"INÍCIO - execute | Prompt: {prompt[:100]}...")
            
            # Configura o modelo
            self.models.configure(
                model=kwargs.get("model", "gpt-3.5-turbo"),
                temperature=kwargs.get("temperature", 0.7)
            )
            
            # Gera resposta
            text, metadata = self.models.generate(prompt)
            
            # Processa o resultado
            result = AgentResult(
                output=text,
                items=[],  # Implementar geração de itens
                guardrails=[],  # Implementar verificação de guardrails
                raw_responses=[{
                    "id": metadata.get("id"),
                    "response": metadata
                }]
            )
            
            # Registra no banco de dados
            run_id = self.db.log_run(
                session_id=kwargs.get("session_id", "default"),
                input=prompt,
                final_output=result.output,
                last_agent="OpenAI",
                output_type=kwargs.get("format", "json")  # Usa o formato passado nos kwargs
            )
            
            # Registra itens gerados
            for item in result.items:
                self.db.log_run_item(run_id, "item", item)
                
            # Registra guardrails
            for guardrail in result.guardrails:
                self.db.log_guardrail_results(run_id, "output", guardrail)
                
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
    user_prompt = "Preciso de um sistema de login com autenticação de dois fatores"
    result = orchestrator.execute(user_prompt)
    print("Resultado Final:", result.output)
