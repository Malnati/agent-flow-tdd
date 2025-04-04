# src/mpc.py
"""
Módulo para lidar com o protocolo MCP (Model Context Protocol).
"""
import json
import logging
import os
import sys
import uuid
from typing import Optional, Dict, Any

from src.app import AgentOrchestrator
from src.core.logger import trace, agent_span, generation_span
from src.core.models import ModelManager
from src.core.db import DatabaseManager

from openai import OpenAI

# Configuração básica de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/mcp_server.log")
    ]
)

logger = logging.getLogger(__name__)

try:
    from mcp_sdk import BaseMCPHandler, Message, Response
except ImportError:
    # Mock classes para testes
    class Message:
        """Mock da classe Message do SDK MCP."""
        def __init__(self, content: str, metadata: Dict[str, Any]):
            self.content = content
            self.metadata = metadata

    class Response:
        """Mock da classe Response do SDK MCP."""
        def __init__(self, content: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
            self.content = content
            self.metadata = metadata or {}

    class BaseMCPHandler:
        """Mock da classe BaseMCPHandler do SDK MCP."""
        def __init__(self):
            self.initialized = False
            self.hook = "/prompt-tdd"

        def initialize(self, api_key: str) -> None:
            """Inicializa o handler com a chave da API."""
            self.initialized = True

        def run(self) -> None:
            """Executa o loop principal do handler."""
            while True:
                try:
                    line = sys.stdin.readline()
                    if not line:
                        break

                    data = json.loads(line)
                    message = Message(data["content"], data["metadata"])
                    response = self.handle_message(message)
                    print(json.dumps({
                        "content": response.content,
                        "metadata": response.metadata
                    }))
                except Exception as e:
                    logging.error(f"Erro ao processar mensagem: {str(e)}")
                    break

        def handle_message(self, message: Message) -> Response:
            """Processa uma mensagem e retorna uma resposta."""
            raise NotImplementedError()


class PromptManager:
    def __init__(self):
        self.templates: Dict[str, str] = {}
        logger.info("PromptManager inicializado")
        
    def add_template(self, name: str, template: str) -> None:
        """Adiciona um novo template de prompt."""
        self.templates[name] = template
        logger.info(f"Template '{name}' adicionado")
        
    def get_template(self, name: str) -> Optional[str]:
        """Recupera um template de prompt pelo nome."""
        template = self.templates.get(name)
        if not template:
            logger.warning(f"Template '{name}' não encontrado")
        return template
        
    def format_prompt(self, template_name: str, **kwargs) -> Optional[str]:
        """Formata um prompt usando um template e variáveis."""
        template = self.get_template(template_name)
        if not template:
            return None
            
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Erro ao formatar prompt: variável {e} não fornecida")
            return None
        except Exception as e:
            logger.error(f"Erro ao formatar prompt: {str(e)}")
            return None 

class LLMProvider:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OPENAI_API_KEY não encontrada nas variáveis de ambiente")
        self.client = OpenAI(api_key=self.api_key)
        
    def generate(self, prompt: str, options: Dict[str, Any]) -> Optional[str]:
        try:
            model = options.get("model", "gpt-3.5-turbo")
            temperature = options.get("temperature", 0.7)
            format = options.get("format", "json")
            
            logger.info(f"Gerando resposta com modelo {model} (temperatura: {temperature})")
            
            # Ajusta o prompt para gerar resposta no formato correto
            if format == "markdown":
                prompt = f"Por favor, formate sua resposta em Markdown com:\n- Títulos e subtítulos\n- Listas\n- Destaques\n- Tabelas quando relevante\n\nPrompt: {prompt}"
            
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature
            )
            
            content = response.choices[0].message.content
            
            # Retorna sempre um dicionário estruturado
            return {
                "content": content,
                "metadata": {
                    "status": "success",
                    "format": format
                }
            }
                
        except Exception as e:
            logger.error(f"Erro ao gerar resposta: {str(e)}")
            return None

class MCPHandler:
    """Manipulador do protocolo MCP."""

    def __init__(self, llm_provider: 'LLMProvider', prompt_manager: 'PromptManager'):
        """Inicializa o manipulador MCP."""
        self.orchestrator = None
        self.models = ModelManager()
        self.llm_provider = llm_provider
        self.prompt_manager = prompt_manager
        self.db = DatabaseManager()
        self.session_id = str(uuid.uuid4())
        logger.info("MCPHandler inicializado com sucesso")

    def initialize(self, api_key: Optional[str] = None):
        """Inicializa o orquestrador com a chave da API."""
        logger.info("Inicializando MCPHandler...")
        self.orchestrator = AgentOrchestrator(api_key=api_key)
        self.models.configure(
            model="gpt-3.5-turbo",
            temperature=0.7
        )
        logger.info("MCPHandler inicializado com sucesso")

    @trace(workflow_name="MCP Workflow")
    @agent_span()
    def process_message(self, message: Dict[str, Any]) -> Optional[str]:
        """
        Processa uma mensagem recebida.
        
        Args:
            message: Mensagem a ser processada
            
        Returns:
            Resposta processada ou None em caso de erro
        """
        try:
            content = message.get("content")
            metadata = message.get("metadata", {})
            
            if not content:
                logger.warning("Mensagem recebida sem conteúdo")
                return None
                
            logger.info(f"Processando mensagem: {content}")
            logger.info(f"Metadata: {metadata}")
            
            # Registra a execução no banco
            run_id = self.db.log_run(
                session_id=self.session_id,
                input_text=content,
                last_agent=None,  # Será atualizado após a execução
                output_type=metadata.get("options", {}).get("format", "json")
            )
            
            with generation_span(name="LLM Generation"):
                response = self.llm_provider.generate(content, metadata.get("options", {}))
            
            if response:
                # Atualiza o registro com a resposta
                self.db.log_raw_response(run_id, response)
                
                # Registra a resposta final
                self.db.log_run_item(
                    run_id=run_id,
                    item_type="MessageOutput",
                    raw_item={"content": response["content"]}
                )
                
                logger.info(f"Resposta gerada: {response['content']}")
                return response["content"]
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {str(e)}")
            return None

    def handle_message(self, message: Message) -> Response:
        """
        Manipula uma mensagem MCP.
        
        Args:
            message: Mensagem MCP recebida
            
        Returns:
            Resposta MCP formatada
        """
        try:
            # Processa a mensagem
            result = self.process_message({
                "content": message.content,
                "metadata": message.metadata
            })
            
            if result:
                # Busca o último registro do banco para metadados
                history = self.db.get_run_history(limit=1)
                metadata = {}
                
                if history:
                    last_run = history[0]
                    metadata = {
                        "last_agent": last_run["last_agent"],
                        "output_type": last_run["output_type"],
                        "session_id": last_run["session_id"],
                        "items_count": len(last_run["items"]),
                        "guardrails_count": len(last_run["guardrails"]),
                        "raw_responses_count": len(last_run["raw_responses"])
                    }
                
                return Response({"content": result}, metadata=metadata)
            
            return Response({"error": "Falha ao processar mensagem"}, metadata={"status": "error"})
            
        except Exception as e:
            logger.error(f"Erro ao manipular mensagem: {str(e)}")
            return Response({"error": str(e)}, metadata={"status": "error"})

    def run(self):
        """Executa o manipulador MCP."""
        try:
            # Lê o arquivo de pipe
            pipe_file = "logs/mcp_pipe.log"
            logger.info(f"Iniciando leitura do arquivo: {pipe_file}")
            
            with open(pipe_file, "r") as f:
                content = f.read().strip()
                
            if not content:
                logger.warning("Arquivo vazio")
                return
                
            # Processa o conteúdo
            try:
                message_data = json.loads(content)
                message = Message(
                    content=message_data["content"],
                    metadata=message_data.get("metadata", {})
                )
            except json.JSONDecodeError:
                message = Message(content=content, metadata={})
            
            # Processa a mensagem
            self.handle_message(message)
            
            # Remove o arquivo após processamento
            os.remove(pipe_file)
            logger.info("Arquivo removido")
            
        except Exception as e:
            logger.error(f"Erro ao executar MCP: {str(e)}")
            raise

if __name__ == "__main__":
    # Executar como serviço standalone
    llm_provider = LLMProvider()
    prompt_manager = PromptManager()
    handler = MCPHandler(llm_provider, prompt_manager)
    handler.initialize(api_key=None)  # A chave será obtida das variáveis de ambiente
    handler.run()
