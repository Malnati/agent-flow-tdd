"""
Orquestrador de agentes do sistema.
"""
from typing import Any, Dict, List, Optional
import json
import yaml
import os
from pydantic import BaseModel
from jinja2 import Template
from pathlib import Path
import logging

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

class InputGuardrail:
    """Guardrail para processamento de entrada."""
    
    def __init__(self, model_manager: ModelManager):
        """
        Inicializa o guardrail de entrada.
        
        Args:
            model_manager: Gerenciador de modelos para processamento
        """
        self.model_manager = model_manager
        self.config = self._load_config()
        self.requirements = self._load_requirements()
        self.logger = logging.getLogger(__name__)
        logger.info("InputGuardrail inicializado")
        
    def _load_config(self) -> Dict[str, Any]:
        """Carrega configurações do guardrail."""
        config_path = Path("src/configs/kernel.yaml")
        with open(config_path) as f:
            config = yaml.safe_load(f)
            return config["guardrails"]
    
    def _load_requirements(self) -> Dict[str, Any]:
        """Carrega requisitos do arquivo de configuração."""
        return self.config.get("input", {})
    
    def _extract_info_from_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        Extrai informações do prompt usando IA.
        
        Args:
            prompt: Prompt original do usuário
            
        Returns:
            Dicionário com informações extraídas
        """
        try:
            system_prompt = """
            Analise o prompt do usuário e extraia as seguintes informações em formato JSON:
            - name: Nome da funcionalidade
            - description: Descrição detalhada
            - objectives: Lista de objetivos principais
            - requirements: Lista de requisitos (opcional)
            - constraints: Lista de restrições (opcional)
            
            Retorne APENAS o JSON, sem texto adicional.
            """

            response = self.model_manager.generate_response(
                system_prompt=system_prompt,
                user_prompt=prompt
            )

            # Remove espaços e quebras de linha extras
            response = response.strip()
            
            # Tenta extrair apenas o JSON se houver texto adicional
            if response.find('{') >= 0 and response.find('}') >= 0:
                start = response.find('{')
                end = response.rfind('}') + 1
                response = response[start:end]
            
            # Tenta fazer o parse do JSON
            try:
                info = json.loads(response)
                
                # Garante que todos os campos obrigatórios existem
                required_fields = ["name", "description", "objectives"]
                for field in required_fields:
                    if field not in info:
                        info[field] = "Não especificado" if field != "objectives" else ["Implementar a funcionalidade solicitada"]
                
                # Garante que campos opcionais existem
                optional_fields = ["requirements", "constraints"]
                for field in optional_fields:
                    if field not in info:
                        info[field] = []
                        
                return info
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Erro ao decodificar JSON: {str(e)}")
                return {
                    "name": "Funcionalidade",
                    "description": prompt,
                    "objectives": ["Implementar a funcionalidade solicitada"],
                    "requirements": [],
                    "constraints": []
                }
            
        except Exception as e:
            self.logger.error(f"Erro ao extrair informações do prompt: {str(e)}")
            return {
                "name": "Funcionalidade",
                "description": prompt,
                "objectives": ["Implementar a funcionalidade solicitada"],
                "requirements": [],
                "constraints": []
            }
    
    def process(self, prompt: str) -> Dict[str, Any]:
        """
        Processa o prompt aplicando o guardrail.
        
        Args:
            prompt: Prompt original do usuário
            
        Returns:
            Dicionário com resultado do processamento
        """
        logger.info(f"Processando prompt com InputGuardrail: {prompt[:100]}...")
        
        try:
            # Extrai informações do prompt
            info = self._extract_info_from_prompt(prompt)
            
            # Carrega o template
            template_str = self.requirements.get("prompt_template", "")
            if not template_str:
                raise ValueError("Template não encontrado na configuração")
                
            template = Template(template_str)
            
            # Gera o prompt estruturado
            try:
                structured_prompt = template.render(
                    name=info["name"],
                    description=info["description"],
                    objectives=info["objectives"],
                    requirements=info["requirements"],
                    constraints=info["constraints"]
                )
            except Exception as e:
                self.logger.error(f"Erro ao renderizar template: {str(e)}")
                structured_prompt = prompt
            
            return {
                "status": "success",
                "prompt": structured_prompt,
                "info": info
            }
            
        except Exception as e:
            logger.error(f"Erro ao processar prompt: {str(e)}")
            return {
                "status": "error",
                "prompt": prompt,
                "info": None,
                "error": str(e)
            }

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
            guardrail_result = self.input_guardrail.process(prompt)
            
            # Configura o modelo
            self.models.configure(
                model=kwargs.get("model", CONFIG["model"]["name"]),
                temperature=kwargs.get("temperature", CONFIG["model"]["temperature"])
            )
            
            # Usa o prompt estruturado se o guardrail foi bem sucedido
            final_prompt = guardrail_result.get("prompt", prompt) if guardrail_result["status"] == "success" else prompt
            
            # Gera resposta
            text, metadata = self.models.generate(final_prompt)
            
            # Processa o resultado
            result = AgentResult(
                output=text,
                items=[],
                guardrails=[guardrail_result],
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
            
            # Registra guardrails
            self.db.log_guardrail_results(
                run_id=run_id,
                guardrail_type="input",
                results=guardrail_result
            )
            
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
