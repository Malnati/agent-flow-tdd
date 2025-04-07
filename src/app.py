"""
Módulo principal do sistema.
"""


from src.core.agents import AgentOrchestrator
from src.core.models import ModelManager
from src.core.db import DatabaseManager
from src.core.logger import get_logger

logger = get_logger(__name__)

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

def main():
    """Função principal."""
    try:
        # Obtém orquestrador
        orchestrator = get_orchestrator()
        
        # Exemplo de prompt
        prompt = "Criar sistema de login"
        
        # Executa o orquestrador
        result = orchestrator.execute(
            prompt=prompt,
            session_id="app",
            format="json"
        )
        
        # Imprime resultado
        print(result.output)
        
    except Exception as e:
        logger.error(f"Erro na execução: {str(e)}")
        raise
        
if __name__ == "__main__":
    main()
