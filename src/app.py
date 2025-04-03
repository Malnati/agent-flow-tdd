"""
Módulo principal da aplicação.
"""
from typing import Any, Dict, List

from openai import OpenAI
from pydantic import BaseModel

from src.core.db import DatabaseManager
from src.core.logger import setup_logger

logger = setup_logger(__name__)

class AgentResult(BaseModel):
    """Resultado de uma execução do agente."""
    output: Any
    items: List[Dict[str, Any]] = []
    guardrails: List[Dict[str, Any]] = []
    raw_responses: List[Dict[str, Any]] = []

class AgentOrchestrator:
    """Orquestrador de agentes."""
    
    def __init__(self):
        """Inicializa o orquestrador."""
        self.client = OpenAI()
        self.db = DatabaseManager()
        
    def execute(self, prompt: str, **kwargs) -> AgentResult:
        """
        Executa um prompt usando o agente apropriado.
        
        Args:
            prompt: O prompt a ser executado
            **kwargs: Argumentos adicionais para configuração
            
        Returns:
            AgentResult com o resultado da execução
        """
        logger.info(f"INÍCIO - execute | Prompt: {prompt[:100]}...")
        
        try:
            # Executa o prompt usando a API do OpenAI
            response = self.client.chat.completions.create(
                model=kwargs.get("model", "gpt-3.5-turbo"),
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get("temperature", 0.7)
            )
            
            # Processa o resultado
            result = AgentResult(
                output=response.choices[0].message.content,
                items=[],  # Implementar geração de itens
                guardrails=[],  # Implementar verificação de guardrails
                raw_responses=[{
                    "id": response.id,
                    "response": response.model_dump()
                }]
            )
            
            # Registra no banco de dados
            self.db.log_run(
                session_id=kwargs.get("session_id", "default"),
                input=prompt,
                final_output=result.output,
                last_agent="OpenAI",
                output_type="text",
                items=result.items,
                guardrails=result.guardrails,
                raw_responses=result.raw_responses
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
    user_prompt = "Preciso de um sistema de login com autenticação de dois fatores"
    result = orchestrator.execute(user_prompt)
    print("Resultado Final:", result.output)
