"""
Módulo principal do Agent SDK.
"""
import time
import uuid
from typing import List, Dict, Any
import json

from openai.agent import Runner, RunResult
from openai.agent.items import (
    MessageOutputItem, HandoffCallItem, HandoffOutputItem,
    ToolCallItem, ToolCallOutputItem, ReasoningItem
)

from src.core import ModelManager
from src.core.logger import trace, agent_span
from src.core.db import DatabaseManager

class Message:
    def __init__(self, content: str, source: str, timestamp: float):
        self.content = content
        self.source = source
        self.timestamp = timestamp

class ConversationHistory:
    def __init__(self):
        self.messages = []
    
    def add_message(self, message: Message):
        self.messages.append(message)
    
    def get_context(self, window_size=5) -> str:
        return "\n".join([f"{msg.source}: {msg.content}" for msg in self.messages[-window_size:]])

class TriageAgent:
    def __init__(self, model_manager: ModelManager):
        self.model_manager = model_manager
        self.system_prompt = """
        Você é um roteador especializado em desenvolvimento de software. Sua tarefa é analisar a conversa e decidir quais agentes devem ser acionados:
        - Pré-processamento: Quando precisar clarificar requisitos ou processar dados
        - Análise: Quando detectar necessidade de validação técnica ou métricas
        - Visualização: Quando precisar apresentar resultados ou formatar saídas

        Responda apenas com JSON contendo lista de agentes relevantes.
        """
    
    def route(self, context: str) -> List[str]:
        response = self.model_manager.generate(
            prompt=context,
            system_prompt=self.system_prompt,
            temperature=0
        )
        return json.loads(response)

class DeterministicPreprocessingAgent:
    def __init__(self, model_manager: ModelManager):
        self.model_manager = model_manager
        self.system_prompt = """
        Você é um especialista em engenharia de requisitos. Suas tarefas:
        1. Limpeza: Remover ambiguidades e subjetividades
        2. Transformação: Estruturar em formato Feature -> Critérios de Aceite
        3. Agregação: Combinar com histórico mantendo consistência

        Mantenha neutralidade técnica e foco em testabilidade.
        """
    
    def process(self, input_text: str, context: str) -> str:
        prompt = f"Contexto:\n{context}\n\nInput:\n{input_text}"
        return self.model_manager.generate(
            prompt=prompt,
            system_prompt=self.system_prompt,
            temperature=0.3
        )

class AnalyticalAnalysisAgent:
    def __init__(self, model_manager: ModelManager):
        self.model_manager = model_manager
        self.system_prompt = """
        Você é um arquiteto de software experiente. Realize:
        1. Análise Estatística: Quantidade/Complexidade de requisitos
        2. Correlação: Identificar dependências entre requisitos
        3. Regressão: Prever gaps de implementação

        Use métricas técnicas e padrões de mercado.
        """
    
    def analyze(self, processed_data: str, context: str) -> str:
        prompt = f"Dados Processados:\n{processed_data}\n\nContexto:\n{context}"
        return self.model_manager.generate(
            prompt=prompt,
            system_prompt=self.system_prompt,
            temperature=0.5
        )

class ToolVisualizationAgent:
    def __init__(self, model_manager: ModelManager):
        self.model_manager = model_manager
        self.markdown_prompt = """
        Transforme a análise em markdown com:
        - Seções hierárquicas
        - Tabelas comparativas
        - Destaques para pontos críticos
        """
        
        self.json_prompt = """
        Estruture em JSON com:
        - feature (string)
        - acceptance_criteria (array)
        - test_scenarios (array)
        - complexity (int 1-5)
        - dependencies (array)
        """
    
    def visualize(self, analysis: str, format_type: str) -> str:
        prompt = f"Análise:\n{analysis}"
        system_prompt = self.markdown_prompt if format_type == "markdown" else self.json_prompt
        return self.model_manager.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0
        )

class AgentOrchestrator:
    def __init__(self, api_key: str = None):
        self.history = []
        self.model_manager = ModelManager()
        self.db = DatabaseManager()
        self.session_id = str(uuid.uuid4())
        
        if api_key:
            self.model_manager.configure(
                model="gpt-3.5-turbo",
                temperature=0.7
            )
            
        self.runner = Runner()
        self.triage = None  # Será inicializado sob demanda
        self.preprocessor = None
        self.analyst = None
        self.visualizer = None
    
    def _log_run_result(self, result: RunResult, input_text: str) -> None:
        """
        Registra os resultados da execução no banco de dados.
        
        Args:
            result: Resultado da execução do agente
            input_text: Texto de entrada original
        """
        try:
            # Registra a execução principal
            run_id = self.db.log_run(
                session_id=self.session_id,
                input_text=input_text,
                last_agent=result.last_agent.name if result.last_agent else None,
                output_type=str(result.last_agent.output_type) if result.last_agent else None,
                final_output=str(result.final_output) if result.final_output else None
            )
            
            # Registra os novos itens gerados
            for item in result.new_items:
                item_data = {
                    "raw_item": str(item.raw_item),
                    "timestamp": time.time()
                }
                
                if isinstance(item, MessageOutputItem):
                    self.db.log_run_item(run_id, "MessageOutput", item_data)
                
                elif isinstance(item, HandoffCallItem):
                    self.db.log_run_item(
                        run_id, "HandoffCall", item_data,
                        source_agent=str(item.source_agent) if item.source_agent else None,
                        target_agent=str(item.target_agent) if item.target_agent else None
                    )
                
                elif isinstance(item, HandoffOutputItem):
                    self.db.log_run_item(
                        run_id, "HandoffOutput", item_data,
                        source_agent=str(item.source_agent) if item.source_agent else None,
                        target_agent=str(item.target_agent) if item.target_agent else None
                    )
                
                elif isinstance(item, ToolCallItem):
                    self.db.log_run_item(run_id, "ToolCall", item_data)
                
                elif isinstance(item, ToolCallOutputItem):
                    self.db.log_run_item(run_id, "ToolCallOutput", item_data)
                
                elif isinstance(item, ReasoningItem):
                    self.db.log_run_item(run_id, "Reasoning", item_data)
            
            # Registra resultados dos guardrails
            if result.input_guardrail_results:
                self.db.log_guardrail_results(run_id, "input", result.input_guardrail_results)
            
            if result.output_guardrail_results:
                self.db.log_guardrail_results(run_id, "output", result.output_guardrail_results)
            
            # Registra respostas brutas do LLM
            for response in result.raw_responses:
                self.db.log_raw_response(run_id, response.dict())
            
        except Exception as e:
            logger.error(f"Erro ao registrar resultados no banco: {str(e)}")
            raise
    
    @trace(workflow_name="Agent Workflow")
    @agent_span()
    def handle_input(self, user_input: str) -> Dict[str, Any]:
        """
        Processa uma entrada do usuário através do Agent SDK.
        
        Args:
            user_input: Texto de entrada do usuário
            
        Returns:
            Dicionário com o resultado do processamento
        """
        try:
            # Registra entrada do usuário
            self.history.append(Message(user_input, "User", time.time()))
            
            # Executa o runner com os agentes disponíveis
            result = self.runner.run(
                input=user_input,
                agents=[
                    self.triage,
                    self.preprocessor,
                    self.analyst,
                    self.visualizer
                ]
            )
            
            # Registra resultados no banco
            self._log_run_result(result, user_input)
            
            # Processa resultado final
            if result.final_output:
                if isinstance(result.final_output, str):
                    try:
                        return json.loads(result.final_output)
                    except:
                        return {"result": result.final_output}
                return result.final_output
            
            return {"error": "Nenhuma saída gerada"}
            
        except Exception as e:
            logger.error(f"Erro ao processar entrada: {str(e)}")
            return {"error": str(e)}
        
    def get_run_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retorna o histórico das últimas execuções.
        
        Args:
            limit: Número máximo de registros
            
        Returns:
            Lista de execuções com seus detalhes
        """
        return self.db.get_run_history(limit)

# Uso
if __name__ == "__main__":
    import os
    api_key = os.getenv("OPENAI_KEY")
    if not api_key:
        print("ERRO: A variável de ambiente OPENAI_KEY não está definida")
        exit(1)
        
    orchestrator = AgentOrchestrator(api_key=api_key)
    user_prompt = "Preciso de um sistema de login com autenticação de dois fatores"
    result = orchestrator.handle_input(user_prompt)
    print("Resultado Final:", json.dumps(result, indent=2))
