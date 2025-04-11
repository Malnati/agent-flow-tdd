"""
# src/core/agents.py
Módulo de agentes e guardrails do sistema.
"""
from typing import Any, Dict, List, Optional
import json
import os
from pydantic import BaseModel

from src.core import ModelManager
from src.core.logger import get_logger

logger = get_logger(__name__)

def load_config() -> Dict[str, Any]:
    """
    Carrega configurações do sistema.
    
    Returns:
        Dict com configurações
        
    Raises:
        RuntimeError: Quando o arquivo de configuração está ausente ou é inválido
    """
    try:
        # Tenta carregar o arquivo JSON
        agents_config_path = os.path.join(os.path.dirname(__file__), "..", "configs", "agents.json")
        if os.path.exists(agents_config_path):
            with open(agents_config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                logger.info(f"Configurações carregadas com sucesso de: {agents_config_path}")
                return config
        else:
            raise FileNotFoundError(f"Arquivo de configuração não encontrado: {agents_config_path}")
                
    except Exception as e:
        logger.error(f"FALHA - load_config | Erro: {str(e)}")
        raise RuntimeError(f"Erro ao carregar arquivo de configuração: {str(e)}")

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
    prompt_final: str = ""
    guardrails: List[Dict[str, Any]] = []
    raw_responses: List[Dict[str, Any]] = []

class AgentOrchestrator:
    """
    Classe responsável por orquestrar o fluxo completo de processamento.
    """
    
    def __init__(self, model_name=None):
        """
        Inicializa o orquestrador.
        
        Args:
            model_name: Nome do modelo a ser usado
        """
        self.config = self.load_config()
        self.model_manager = ModelManager(model_name)
        self.input_guardrails = {}
        self.output_guardrails = {}
        self.initialize()
        
    def load_config(self):
        """
        Carrega as configurações do agente, tentando primeiro o JSON.
        
        Returns:
            Configurações carregadas
        """
        try:
            # Tenta carregar do arquivo JSON primeiro
            config_path_json = os.path.join(os.path.dirname(__file__), "../configs/agents.json")
            if os.path.exists(config_path_json):
                with open(config_path_json, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    logger.info(f"Configurações carregadas com sucesso de: {os.path.abspath(config_path_json)}")
                    return config
                    
            # Se nenhum arquivo for encontrado
            raise FileNotFoundError("Arquivos de configuração configs/agents.json não encontrados")
            
        except Exception as e:
            logger.error(f"Erro ao carregar configurações: {str(e)}")
            raise
        
    def execute(self, prompt: str, format: str = "text") -> AgentResult:
        """
        Executa o fluxo completo de processamento.
        
        Args:
            prompt: Prompt do usuário
            format: Formato de saída desejado
            
        Returns:
            Resultado do processamento
        """
        try:
            logger.info(f"Iniciando execução para prompt: {prompt[:50]}...")
            
            # Lista para armazenar as respostas dos guardrails
            prompt_responses = []
            raw_responses = []
            
            # Processa cada guardrail de entrada dinamicamente
            for guardrail_id, guardrail in self.input_guardrails.items():
                try:
                    result = guardrail.process(prompt)
                    prompt_responses.append(result)
                    raw_responses.append({"guardrail": guardrail_id, "response": result})
                    logger.debug(f"Texto gerado por {guardrail_id}: {result[:50]}...")
                except Exception as e:
                    logger.warning(f"Falha no guardrail {guardrail_id}: {str(e)}")
                    raw_responses.append({"guardrail": guardrail_id, "error": str(e)})
            
            # Concatena os resultados dos guardrails em um prompt final
            prompt_final = f"{prompt}\n\n" + "\n\n".join(prompt_responses)
            
            # Gera prompt TDD
            try:
                # Processa com o guardrail de saída
                result = self.output_guardrails["gerar_prompt_tdd"].process(prompt_final)
                
                # Verifica coerência (opcional)
                coherence_result = None
                if "verificar_coerencia" in self.output_guardrails:
                    try:
                        coherence_result = self.output_guardrails["verificar_coerencia"].process(
                            f"Resultado: {result}\nPrompt original: {prompt}", 
                            {"original": prompt, "result": result}
                        )
                        logger.debug(f"Resultado da verificação de coerência: {coherence_result}")
                    except Exception as e:
                        logger.warning(f"Erro na verificação de coerência: {str(e)}")
                
                guardrails_metadata = [{"name": "gerar_prompt_tdd", "result": result}]
                if coherence_result:
                    guardrails_metadata.append({"name": "verificar_coerencia", "result": coherence_result})
                
                return AgentResult(
                    output=result,
                    prompt_final=prompt_final,
                    guardrails=guardrails_metadata,
                    raw_responses=raw_responses
                )
                
            except Exception as e:
                logger.error(f"Erro no guardrail de saída: {str(e)}")
                return AgentResult(
                    output=f"Erro na geração do resultado: {str(e)}",
                    prompt_final=prompt_final,
                    guardrails=[],
                    raw_responses=raw_responses
                )
                
        except Exception as e:
            logger.error(f"FALHA - execute | Erro: {str(e)}")
            raise Exception(f"Erro crítico na execução do agente")

    def initialize(self):
        """
        Inicializa os componentes do agente.
        """
        # Inicializa os guardrails de entrada
        input_guardrails = {}
        for guardrail_id, guardrail_config in self.config["GuardRails"]["Input"].items():
            input_guardrails[guardrail_id] = InputGuardrail(
                guardrail_id=guardrail_id,
                config=guardrail_config,
                model_manager=self.model_manager
            )
            logger.info("InputGuardrail inicializado")
        
        # Inicializa os guardrails de saída
        output_guardrails = {}
        for guardrail_id, guardrail_config in self.config["GuardRails"]["Output"].items():
            output_guardrails[guardrail_id] = OutputGuardrail(
                guardrail_name=guardrail_id,
                config=guardrail_config,
                model_manager=self.model_manager
            )
            logger.info("OutputGuardrail inicializado")
            
        self.input_guardrails = input_guardrails
        self.output_guardrails = output_guardrails
        
        logger.info("AgentOrchestrator inicializado")

class InputGuardrail:
    """Guardrail para geração de sugestões e complementos ao prompt do usuário."""
    
    def __init__(self, guardrail_id: str, config: dict, model_manager):
        """
        Inicializa o guardrail.
        
        Args:
            guardrail_id: ID do guardrail
            config: Configuração do guardrail
            model_manager: Gerenciador de modelos
        """
        self.guardrail_id = guardrail_id
        self.config = config
        self.model_manager = model_manager
        self.requirements = config.get("requirements", "")
        logger.info("InputGuardrail inicializado")
        
    def process(self, prompt: str) -> str:
        """
        Processa o prompt e gera uma resposta textual como sugestão ou complemento.
        
        Args:
            prompt: Prompt do usuário
            
        Returns:
            Texto com sugestões ou complementos ao prompt
        """
        try:
            # Log do prompt original para debug
            logger.debug(f"Prompt original: {prompt}")
            
            # Gera resposta com o modelo
            messages = [
                {"role": "system", "content": self.config["system_prompt"]},
                {"role": "user", "content": prompt}
            ]
            
            response = self.model_manager.generate_response(messages)
            logger.debug(f"Resposta do modelo: {response}")
            
            # Limpa o output se estiver em formato de bloco de código
            cleaned_response = response
            if cleaned_response.startswith("```") and "```" in cleaned_response[3:]:
                first_delimiter_end = cleaned_response.find("\n", 3)
                if first_delimiter_end != -1:
                    last_delimiter_start = cleaned_response.rfind("```")
                    if last_delimiter_start > first_delimiter_end:
                        cleaned_response = cleaned_response[first_delimiter_end+1:last_delimiter_start].strip()
            
            return cleaned_response
            
        except Exception as e:
            logger.error(f"FALHA - process | Erro: {str(e)}")
            return f"Erro no processamento do guardrail {self.guardrail_id}: {str(e)}"

class OutputGuardrail:
    """
    Classe que implementa o guardrail para geração da saída final.
    """
    
    def __init__(self, guardrail_name: str, config: dict, model_manager):
        """
        Inicializa o guardrail.
        
        Args:
            guardrail_name: Nome do guardrail
            config: Configuração do guardrail
            model_manager: Gerenciador de modelos
        """
        self.name = guardrail_name
        self.config = config
        self.model_manager = model_manager
        self.format = config.get("format", "text")
        self.requirements = config.get("requirements", "")
        
    def process(self, prompt: str, context: dict = None) -> str:
        """
        Processa o prompt final e gera a saída.
        
        Args:
            prompt: Prompt final com todas as contribuições
            context: Contexto adicional com dados para o guardrail (opcional)
            
        Returns:
            Resposta textual gerada
        """
        if not context:
            context = {}
        
        try:
            logger.debug(f"Processando guardrail output {self.name}")
            
            # Gera resposta com o modelo
            messages = [
                {"role": "system", "content": self.config["completion_prompt"]},
                {"role": "user", "content": prompt}
            ]
            
            output = self.model_manager.generate_response(messages)
            logger.debug(f"Saída do modelo: {output[:100]}...")
            
            # Limpa o output se estiver em formato de bloco de código
            cleaned_output = output
            if cleaned_output.startswith("```") and "```" in cleaned_output[3:]:
                first_delimiter_end = cleaned_output.find("\n", 3)
                if first_delimiter_end != -1:
                    last_delimiter_start = cleaned_output.rfind("```")
                    if last_delimiter_start > first_delimiter_end:
                        cleaned_output = cleaned_output[first_delimiter_end+1:last_delimiter_start].strip()
                        logger.debug(f"Output limpo de marcadores de código: {cleaned_output[:100]}...")
            
            # Retorna o texto sem validações estruturais
            return cleaned_output
                
        except Exception as e:
            logger.error(f"FALHA - process | Erro: {str(e)}")
            return f"Erro ao processar o guardrail de saída: {str(e)}"
