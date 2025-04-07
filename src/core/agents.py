"""
Módulo de agentes e guardrails do sistema.
"""
from typing import Any, Dict, List, Optional
import yaml
import os
from pydantic import BaseModel
import uuid

from src.core import ModelManager
from src.core.db import DatabaseManager
from src.core.logger import get_logger

logger = get_logger(__name__)

def load_config() -> Dict[str, Any]:
    """
    Carrega configurações do sistema.
    
    Returns:
        Dict com configurações
    """
    config_path = os.path.join(os.path.dirname(__file__), "..", "configs", "kernel.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config

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
    items: List[Dict[str, Any]] = []
    guardrails: List[Dict[str, Any]] = []
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

    def execute(self, prompt: str, format: str = "json") -> AgentResult:
        """
        Executa o fluxo do agente.
        
        Args:
            prompt: Prompt do usuário
            format: Formato de saída (json/markdown)
            
        Returns:
            Resultado da execução
        """
        try:
            # Registra execução
            run_id = self.db.log_run(
                session_id=str(uuid.uuid4()),
                input=prompt,
                output_type=format
            )

            # Valida entrada
            input_result = self.input_guardrail.process(prompt)
            self.db.log_guardrail_results(
                run_id=run_id,
                guardrail_type="input",
                results={
                    "prompt": prompt,
                    "info": input_result.get("info", {}),
                    "status": input_result.get("status", "error"),
                    "passed": input_result.get("status") == "success"
                }
            )

            if input_result.get("status") != "success":
                raise ValueError(input_result.get("error", "Erro desconhecido"))

            # Gera resposta
            response = self.model_manager.generate_response(
                prompt=prompt,
                system_prompt=CONFIG["prompts"]["system"]
            )

            # Valida saída
            output_result = self.output_guardrail.process(response)
            self.db.log_guardrail_results(
                run_id=run_id,
                guardrail_type="output",
                results={
                    "response": response,
                    "info": output_result.get("info", {}),
                    "status": output_result.get("status", "error"),
                    "passed": output_result.get("status") == "success"
                }
            )

            if output_result.get("status") != "success":
                raise ValueError(output_result.get("error", "Erro desconhecido"))

            # Registra resposta
            self.db.log_raw_response(run_id, response)

            # Retorna resultado
            return AgentResult(
                output=response,
                items=[{"type": "response", "content": response}],
                guardrails=[input_result, output_result],
                raw_responses=[{"id": "response", "response": response}]
            )

        except Exception as e:
            logger.error(f"FALHA - execute | Erro: {str(e)}")
            raise

class InputGuardrail:
    """Guardrail para validação e estruturação de entrada."""
    
    def __init__(self, model_manager: ModelManager):
        """
        Inicializa o guardrail.
        
        Args:
            model_manager: Gerenciador de modelos
        """
        self.model_manager = model_manager
        self.config = self._load_config()
        self.requirements = self._load_requirements()
        logger.info("InputGuardrail inicializado")
        
    def _load_config(self) -> Dict[str, Any]:
        """Carrega configurações do guardrail."""
        return CONFIG["guardrails"]["input"]
        
    def _load_requirements(self) -> Dict[str, Any]:
        """Carrega requisitos do prompt."""
        return self.config["requirements"]
        
    def _extract_info_from_prompt(self, prompt: str) -> dict:
        """
        Extrai informações estruturadas do prompt.
        
        Args:
            prompt: Prompt do usuário
            
        Returns:
            Dict com informações extraídas
        """
        try:
            # Gera resposta com o modelo
            messages = [
                {"role": "system", "content": self.config["system_prompt"]},
                {"role": "user", "content": prompt}
            ]
            
            response = self.model_manager.generate_response(messages)
            
            # Tenta fazer parse do JSON
            try:
                info = yaml.safe_load(response)
                if not isinstance(info, dict):
                    raise ValueError("Resposta não é um dicionário")
                return info
            except Exception as e:
                logger.error(f"FALHA - _extract_info_from_prompt | Erro ao fazer parse: {str(e)}")
                return self._get_default_json()
                
        except Exception as e:
            logger.error(f"FALHA - _extract_info_from_prompt | Erro: {str(e)}")
            return self._get_default_json()
            
    def _get_default_json(self) -> dict:
        """Retorna JSON padrão para casos de erro."""
        return {
            "type": "feature",
            "description": "",
            "acceptance_criteria": [],
            "test_scenarios": []
        }
        
    def process(self, prompt: str) -> Dict[str, Any]:
        """
        Processa e valida o prompt de entrada.
        
        Args:
            prompt: Prompt do usuário
            
        Returns:
            Dict com resultado do processamento
        """
        try:
            # Extrai informações do prompt
            info = self._extract_info_from_prompt(prompt)
            
            # Valida campos obrigatórios
            missing_fields = []
            for field, required in self.requirements.items():
                if required and field not in info:
                    missing_fields.append(field)
                    
            if missing_fields:
                return {
                    "status": "error",
                    "error": f"Campos obrigatórios ausentes: {', '.join(missing_fields)}",
                    "prompt": prompt
                }
                
            return {
                "status": "success",
                "prompt": prompt,
                "info": info
            }
            
        except Exception as e:
            logger.error(f"FALHA - process | Erro: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "prompt": prompt
            }

class OutputGuardrail:
    """Guardrail para validação e estruturação de saída."""
    
    def __init__(self, model_manager: ModelManager):
        """
        Inicializa o guardrail.
        
        Args:
            model_manager: Gerenciador de modelos
        """
        self.model_manager = model_manager
        self.config = self._load_config()
        self.requirements = self._load_requirements()
        logger.info("OutputGuardrail inicializado")
        
    def _load_config(self) -> Dict[str, Any]:
        """Carrega configurações do guardrail."""
        return CONFIG["guardrails"]["output"]
        
    def _load_requirements(self) -> Dict[str, Any]:
        """Carrega requisitos da saída."""
        return self.config["requirements"]
        
    def _validate_json(self, data: Dict[str, Any]) -> List[str]:
        """
        Valida campos obrigatórios no JSON.
        
        Args:
            data: Dados a serem validados
            
        Returns:
            Lista de campos ausentes
        """
        missing_fields = []
        for field, required in self.requirements.items():
            if required and field not in data:
                missing_fields.append(field)
        return missing_fields
        
    def _suggest_missing_fields(self, data: Dict[str, Any], missing_fields: List[str], context: str) -> Dict[str, Any]:
        """
        Sugere valores para campos ausentes.
        
        Args:
            data: Dados existentes
            missing_fields: Campos ausentes
            context: Contexto para geração
            
        Returns:
            Dict com sugestões
        """
        try:
            # Gera resposta com o modelo
            messages = [
                {"role": "system", "content": self.config["completion_prompt"]},
                {"role": "user", "content": f"Contexto: {context}\nCampos ausentes: {', '.join(missing_fields)}"}
            ]
            
            response = self.model_manager.generate_response(messages)
            
            # Tenta fazer parse do JSON
            try:
                suggestions = yaml.safe_load(response)
                if not isinstance(suggestions, dict):
                    raise ValueError("Resposta não é um dicionário")
                    
                # Atualiza dados com sugestões
                for field in missing_fields:
                    if field in suggestions:
                        data[field] = suggestions[field]
                        
                return data
                
            except Exception as e:
                logger.error(f"FALHA - _suggest_missing_fields | Erro ao fazer parse: {str(e)}")
                return data
                
        except Exception as e:
            logger.error(f"FALHA - _suggest_missing_fields | Erro: {str(e)}")
            return data
            
    def process(self, output: str, context: str) -> Dict[str, Any]:
        """
        Processa e valida a saída.
        
        Args:
            output: Saída do modelo
            context: Contexto da geração
            
        Returns:
            Dict com resultado do processamento
        """
        try:
            # Tenta fazer parse do JSON
            try:
                data = yaml.safe_load(output)
                if not isinstance(data, dict):
                    raise ValueError("Saída não é um dicionário")
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Erro ao fazer parse da saída: {str(e)}",
                    "output": output
                }
                
            # Valida campos obrigatórios
            missing_fields = self._validate_json(data)
            
            if missing_fields:
                # Tenta sugerir valores para campos ausentes
                data = self._suggest_missing_fields(data, missing_fields, context)
                
                # Valida novamente
                missing_fields = self._validate_json(data)
                
                if missing_fields:
                    return {
                        "status": "error",
                        "error": f"Campos obrigatórios ausentes: {', '.join(missing_fields)}",
                        "output": output
                    }
                    
            return {
                "status": "success",
                "output": output,
                "data": data
            }
            
        except Exception as e:
            logger.error(f"FALHA - process | Erro: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "output": output
            }
