"""
# src/core/models.py
Gerenciador de modelos de IA com suporte a múltiplos provedores e fallback automático.
"""
from enum import Enum
from typing import Any, Dict, Optional, Tuple, List
import os
import json
import yaml
from pathlib import Path
from dataclasses import dataclass
import requests

import google.generativeai as genai
from pydantic import BaseModel
from openai import OpenAI
from anthropic import Anthropic

from src.core.kernel import get_env_var
from src.core.logger import get_logger
from src.core.db import DatabaseManager

logger = get_logger(__name__)

@dataclass
class AgentResult:
    """Resultado da execução do agente."""
    output: str
    raw_responses: List[str]
    created_at: str
    id: Optional[str] = None
    prompt: Optional[str] = None
    updated_at: Optional[str] = None

def load_config() -> Dict[str, Any]:
    """
    Carrega as configurações do model manager do arquivo YAML.
    
    Returns:
        Dict com as configurações
    """
    base_dir = Path(__file__).resolve().parent.parent.parent
    config_path = os.path.join(base_dir, 'src', 'configs', 'kernel.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
        return config["models"]

class ModelProvider(str, Enum):
    """Provedores de modelos suportados."""
    OPENAI = "openai"
    OPENROUTER = "openrouter"
    GEMINI = "gemini"
    TINYLLAMA = "tinyllama"
    PHI1 = "phi1"
    DEEPSEEK_LOCAL = "deepseek_local"
    PHI3 = "phi3"

class ModelConfig(BaseModel):
    """Configuração de um modelo."""
    provider: ModelProvider
    model_id: str
    api_key: str
    timeout: int
    max_retries: int
    temperature: float
    max_tokens: Optional[int]

class ModelManager:
    """Gerenciador de modelos de IA."""

    def __init__(self, model_name: Optional[str] = None):
        """
        Inicializa o gerenciador com configurações do modelo.
        
        Args:
            model_name: Nome do modelo a ser usado (opcional)
        """
        self.registry = ModelRegistry()
        self.config = self.registry.config
        env = self.registry.get_env_vars()
        defaults = self.registry.get_defaults()
        self.model_name = model_name or get_env_var(env['default_model'], defaults['model'])
        self.elevation_model = get_env_var(env['elevation_model'], defaults['elevation_model'])
        
        # Configurações de retry e timeout
        self.max_retries = int(get_env_var(env['max_retries'], str(defaults['max_retries'])))
        self.timeout = int(get_env_var(env['model_timeout'], str(defaults['timeout'])))
        
        # Configuração de fallback
        self.fallback_enabled = get_env_var(env['fallback_enabled'], str(self.config['fallback']['enabled'])).lower() == 'true'
        
        # Cache de respostas
        self.cache_enabled = get_env_var(env['cache_enabled'], str(self.config['cache']['enabled'])).lower() == 'true'
        self.cache_ttl = int(get_env_var(env['cache_ttl'], str(self.config['cache']['ttl'])))
        
        # Inicializa banco de dados
        self.db = DatabaseManager()
        
        # Inicializa clientes
        self._setup_clients()
        
        # Configurações padrão
        self.temperature = defaults['temperature']
        self.max_tokens = defaults['max_tokens']
        
        logger.info(f"ModelManager inicializado com modelo {self.model_name}")

    def configure(self, model: Optional[str] = None, temperature: float = None, max_tokens: Optional[int] = None) -> None:
        """
        Configura parâmetros do modelo.
        
        Args:
            model: Nome do modelo a ser usado
            temperature: Temperatura para geração (0.0 a 1.0)
            max_tokens: Número máximo de tokens na resposta
        """
        if model:
            self.model_name = model
        if temperature is not None:
            self.temperature = temperature
        if max_tokens is not None:
            self.max_tokens = max_tokens
        
        logger.info(f"ModelManager configurado: model={self.model_name}, temperature={self.temperature}, max_tokens={self.max_tokens}")

    def _setup_cache(self) -> None:
        """Configura diretório de cache"""
        if self.cache_enabled:
            os.makedirs(self.cache_dir, exist_ok=True)
            
    def _setup_clients(self) -> None:
        """Inicializa clientes para diferentes provedores"""
        env = self.registry.get_env_vars()
        
        # OpenAI
        self.openai_client = OpenAI(
            api_key=get_env_var(env['openai_key']),
            timeout=self.timeout
        )
        
        # OpenRouter (opcional)
        openrouter_key = get_env_var(env['openrouter_key'])
        if openrouter_key:
            self.openrouter_client = OpenAI(
                base_url=self.registry.get_provider_config('openrouter')['base_url'],
                api_key=openrouter_key,
                timeout=self.timeout
            )
        else:
            self.openrouter_client = None
            
        # Gemini (opcional)
        gemini_key = get_env_var(env['gemini_key'])
        if gemini_key:
            genai.configure(api_key=gemini_key)
            self.gemini_model = genai.GenerativeModel(self.registry.get_provider_config('gemini')['default_model'])
        else:
            self.gemini_model = None
            
        # Anthropic (opcional)
        anthropic_key = get_env_var(env['anthropic_key'])
        if anthropic_key:
            self.anthropic_client = Anthropic(api_key=anthropic_key)
        else:
            self.anthropic_client = None

        # TinyLLaMA
        try:
            from llama_cpp import Llama
            tinyllama_config = self.registry.get_provider_config('tinyllama')
            model_path = tinyllama_config['model_path']
            
            # Verifica se o modelo existe
            if os.path.exists(model_path) and os.path.getsize(model_path) > 1000000:  # Tamanho mínimo de 1MB
                try:
                    # Primeira tentativa - API mais recente
                    self.tinyllama_model = Llama(
                        model_path=model_path,
                        n_ctx=tinyllama_config['n_ctx'],
                        n_threads=tinyllama_config['n_threads']
                    )
                    logger.info(f"TinyLLaMA carregado com sucesso: {model_path}")
                except TypeError as e:
                    if "positional arguments but 3 were given" in str(e):
                        # Segunda tentativa - API mais antiga
                        # Passar apenas o caminho do modelo
                        self.tinyllama_model = Llama(model_path)
                        logger.info(f"TinyLLaMA carregado com API legada: {model_path}")
                    else:
                        raise
            else:
                logger.warning(f"Arquivo de modelo TinyLLaMA não encontrado ou muito pequeno: {model_path}")
                self.tinyllama_model = None
        except (ImportError, FileNotFoundError, ValueError) as e:
            logger.warning(f"TinyLLaMA não disponível: {str(e)}")
            self.tinyllama_model = None
            
        # Phi-1
        try:
            from llama_cpp import Llama
            phi1_config = self.registry.get_provider_config('phi1')
            model_path = phi1_config['model_path']
            
            # Verifica se o modelo existe
            if os.path.exists(model_path) and os.path.getsize(model_path) > 1000000:  # Tamanho mínimo de 1MB
                try:
                    # Primeira tentativa - API mais recente
                    self.phi1_model = Llama(
                        model_path=model_path,
                        n_ctx=phi1_config['n_ctx'],
                        n_threads=phi1_config['n_threads']
                    )
                    logger.info(f"Phi-1 carregado com sucesso: {model_path}")
                except TypeError as e:
                    if "positional arguments but 3 were given" in str(e):
                        # Segunda tentativa - API mais antiga
                        # Passar apenas o caminho do modelo
                        self.phi1_model = Llama(model_path)
                        logger.info(f"Phi-1 carregado com API legada: {model_path}")
                    else:
                        raise
            else:
                logger.warning(f"Arquivo de modelo Phi-1 não encontrado ou muito pequeno: {model_path}")
                self.phi1_model = None
        except (ImportError, FileNotFoundError, ValueError) as e:
            logger.warning(f"Phi-1 não disponível: {str(e)}")
            self.phi1_model = None
        
        # DeepSeek Coder
        try:
            from llama_cpp import Llama
            deepseek_config = self.registry.get_provider_config('deepseek_local')
            model_path = deepseek_config['model_path']
            
            # Verifica se o modelo existe
            if os.path.exists(model_path) and os.path.getsize(model_path) > 1000000:  # Tamanho mínimo de 1MB
                try:
                    # Primeira tentativa - API mais recente
                    self.deepseek_model = Llama(
                        model_path=model_path,
                        n_ctx=deepseek_config['n_ctx'],
                        n_threads=deepseek_config['n_threads']
                    )
                    logger.info(f"DeepSeek Coder carregado com sucesso: {model_path}")
                except TypeError as e:
                    if "positional arguments but 3 were given" in str(e):
                        # Segunda tentativa - API mais antiga
                        # Passar apenas o caminho do modelo
                        self.deepseek_model = Llama(model_path)
                        logger.info(f"DeepSeek Coder carregado com API legada: {model_path}")
                    else:
                        raise
            else:
                logger.warning(f"Arquivo de modelo DeepSeek Coder não encontrado ou muito pequeno: {model_path}")
                self.deepseek_model = None
        except (ImportError, FileNotFoundError, ValueError) as e:
            logger.warning(f"DeepSeek Coder não disponível: {str(e)}")
            self.deepseek_model = None
            
        # Phi-3 Mini
        try:
            from llama_cpp import Llama
            phi3_config = self.registry.get_provider_config('phi3')
            model_path = phi3_config['model_path']
            
            # Verifica se o modelo existe
            if os.path.exists(model_path) and os.path.getsize(model_path) > 1000000:  # Tamanho mínimo de 1MB
                try:
                    # Primeira tentativa - API mais recente
                    self.phi3_model = Llama(
                        model_path=model_path,
                        n_ctx=phi3_config['n_ctx'],
                        n_threads=phi3_config['n_threads']
                    )
                    logger.info(f"Phi-3 Mini carregado com sucesso: {model_path}")
                except TypeError as e:
                    if "positional arguments but 3 were given" in str(e):
                        # Segunda tentativa - API mais antiga
                        # Passar apenas o caminho do modelo
                        self.phi3_model = Llama(model_path)
                        logger.info(f"Phi-3 Mini carregado com API legada: {model_path}")
                    else:
                        raise
            else:
                logger.warning(f"Arquivo de modelo Phi-3 Mini não encontrado ou muito pequeno: {model_path}")
                self.phi3_model = None
        except (ImportError, FileNotFoundError, ValueError) as e:
            logger.warning(f"Phi-3 Mini não disponível: {str(e)}")
            self.phi3_model = None

    def _get_cache_key(self, prompt: str, system: Optional[str] = None, **kwargs) -> str:
        """
        Gera chave de cache para um prompt.
        
        Args:
            prompt: Prompt para o modelo
            system: Prompt de sistema (opcional)
            **kwargs: Argumentos adicionais
            
        Returns:
            String com a chave de cache
        """
        cache_key = {
            "prompt": prompt,
            "system": system,
            "model": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            **kwargs
        }
        return json.dumps(cache_key, sort_keys=True)
        
    def _get_cached_response(self, cache_key: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Obtém resposta do cache se disponível.
        
        Args:
            cache_key: Chave de cache
            
        Returns:
            Tupla (resposta, metadados) se encontrada, None caso contrário
        """
        if not self.cache_enabled:
            return None
            
        return self.db.get_cached_response(cache_key, self.cache_ttl)
            
    def _save_to_cache(self, cache_key: str, response: str, metadata: Dict[str, Any]) -> None:
        """
        Salva resposta no cache.
        
        Args:
            cache_key: Chave de cache
            response: Resposta do modelo
            metadata: Metadados da resposta
        """
        if not self.cache_enabled:
            return
            
        try:
            self.db.save_to_cache(cache_key, response, metadata)
        except Exception as e:
            logger.error(f"Erro ao salvar cache: {str(e)}")
            
    def _get_provider(self, model: str) -> str:
        """
        Identifica o provedor com base no nome do modelo.
        
        Args:
            model: Nome do modelo
            
        Returns:
            String com o nome do provedor
        """
        return self.registry.get_provider_name(model)

    def _get_provider_config(self, provider: str) -> Dict[str, Any]:
        """
        Obtém configurações específicas do provedor.
        
        Args:
            provider: Nome do provedor
            
        Returns:
            Dict com configurações do provedor
        """
        return self.registry.get_provider_config(provider)

    def _generate_with_provider(
        self,
        provider: str,
        prompt: str,
        system: Optional[str] = None,
        **kwargs
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Gera resposta usando um provedor específico.
        
        Args:
            provider: Nome do provedor
            prompt: Prompt para o modelo
            system: Prompt de sistema (opcional)
            **kwargs: Argumentos adicionais
            
        Returns:
            Tupla (resposta, metadados)
            
        Raises:
            ValueError: Se o provedor não estiver disponível
        """
        logger.info(f"Gerando resposta com provedor: {provider}")
        
        # Verifica se o modelo está disponível
        if provider == 'deepseek_local' and not self.deepseek_model:
            logger.error("Modelo DeepSeek Coder não está disponível.")
            raise ValueError("Modelo DeepSeek Coder não está disponível. Verifique se o arquivo do modelo está presente e acessível.")
        elif provider == 'phi3' and not self.phi3_model:
            logger.error("Modelo Phi-3 Mini não está disponível.")
            raise ValueError("Modelo Phi-3 Mini não está disponível. Verifique se o arquivo do modelo está presente e acessível.")
        
        if provider == 'openai':
            return self._generate_openai(prompt, system, **kwargs)
        elif provider == 'openrouter':
            if not self.openrouter_client:
                if not self.fallback_enabled:
                    raise ValueError("OpenRouter não configurado")
                else:
                    return self._generate_openai(prompt, system, **kwargs)
            # Usar o cliente OpenRouter diretamente (não chamar _generate_openai)
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            
            response = self.openrouter_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=kwargs.get('temperature', self.temperature),
                max_tokens=kwargs.get('max_tokens', self.max_tokens)
            )
            
            return response.choices[0].message.content, {
                "model": response.model,
                "usage": response.usage.model_dump(),
                "status": "success"
            }
        elif provider == 'gemini':
            if not self.gemini_model:
                if not self.fallback_enabled:
                    raise ValueError("Gemini não configurado")
                else:
                    return self._generate_openai(prompt, system, **kwargs)
            return self._generate_gemini(prompt, system, **kwargs)
        elif provider == 'anthropic':
            if not self.anthropic_client:
                if not self.fallback_enabled:
                    raise ValueError("Anthropic não configurado")
                else:
                    return self._generate_openai(prompt, system, **kwargs)
            return self._generate_anthropic(prompt, system, **kwargs)
        elif provider == 'tinyllama':
            if not self.tinyllama_model:
                if not self.fallback_enabled:
                    raise ValueError("TinyLLaMA não configurado")
                else:
                    return self._generate_openai(prompt, system, **kwargs)
            return self._generate_tinyllama(prompt, system, **kwargs)
        elif provider == 'phi1':
            if not self.phi1_model:
                if not self.fallback_enabled:
                    raise ValueError("Phi-1 não configurado")
                else:
                    return self._generate_openai(prompt, system, **kwargs)
            return self._generate_phi1(prompt, system, **kwargs)
        elif provider == 'deepseek_local':
            if not self.deepseek_model:
                if not self.fallback_enabled:
                    raise ValueError("DeepSeek Coder não configurado")
                else:
                    return self._generate_openai(prompt, system, **kwargs)
            return self._generate_deepseek(prompt, system, **kwargs)
        elif provider == 'phi3':
            if not self.phi3_model:
                if not self.fallback_enabled:
                    raise ValueError("Phi-3 Mini não configurado")
                else:
                    return self._generate_openai(prompt, system, **kwargs)
            return self._generate_phi3(prompt, system, **kwargs)
        else:
            raise ValueError(f"Provedor {provider} não suportado")

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        use_cache: bool = True,
        **kwargs
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Gera uma resposta usando o modelo configurado.
        
        Args:
            prompt: Prompt para o modelo
            system: Prompt de sistema (opcional)
            use_cache: Se deve usar cache
            **kwargs: Argumentos adicionais
            
        Returns:
            Tupla (resposta, metadados)
        """
        # Verifica cache
        if use_cache and self.cache_enabled:
            cache_key = self._get_cache_key(prompt, system, **kwargs)
            cached = self._get_cached_response(cache_key)
            if cached:
                return cached

        # Identifica provedor
        provider = self._get_provider(self.model_name)
        
        # Tenta gerar resposta
        for attempt in range(self.max_retries):
            try:
                response, metadata = self._generate_with_provider(
                    provider,
                    prompt,
                    system,
                    **kwargs
                )
                
                if metadata['status'] == 'success':
                    # Salva no cache
                    if use_cache and self.cache_enabled:
                        self._save_to_cache(cache_key, response, metadata)
                    return response, metadata
                    
                # Se falhou e fallback está habilitado, tenta outro provedor
                if self.fallback_enabled and attempt == self.max_retries - 1:
                    logger.warning(f"Fallback para modelo {self.elevation_model}")
                    self.model_name = self.elevation_model
                    provider = self._get_provider(self.model_name)
                    continue
                    
            except Exception as e:
                logger.error(f"Tentativa {attempt + 1} falhou: {str(e)}")
                if attempt == self.max_retries - 1:
                    return "", {
                        "error": str(e),
                        "model": self.model_name,
                        "provider": provider,
                        "status": "error"
                    }
                    
        return "", {
            "error": "Máximo de tentativas excedido",
            "model": self.model_name,
            "provider": provider,
            "status": "error"
        }

    def get_available_models(self) -> Dict[str, list]:
        return self.registry.get_available_models()

    def generate_response(self, messages: list, **kwargs) -> str:
        """
        Gera uma resposta usando o modelo para um conjunto de mensagens.

        Args:
            messages: Lista de mensagens no formato [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
            **kwargs: Argumentos adicionais para o modelo

        Returns:
            Resposta gerada
        """
        try:
            # Extrair o prompt do usuário e o prompt do sistema, se fornecidos
            system_prompt = ""
            user_prompt = ""
            
            for msg in messages:
                if msg["role"] == "system":
                    system_prompt = msg["content"]
                elif msg["role"] == "user":
                    user_prompt = msg["content"]
            
            # Usa o método interno que já está implementado corretamente
            response = self._generate_with_model(system_prompt, user_prompt)
            
            if response is None:
                raise ValueError("Falha ao gerar resposta com o modelo")
                
            return response
            
        except Exception as e:
            logger.error(f"Erro ao gerar com {self.model_name}: {str(e)}")
            if self.fallback_enabled:
                # Tenta novamente com modelo de fallback
                original_model = self.model_name
                try:
                    # Configura para usar o modelo de fallback
                    self.model_name = self.elevation_model
                    system_prompt = ""
                    user_prompt = ""
                    
                    for msg in messages:
                        if msg["role"] == "system":
                            system_prompt = msg["content"]
                        elif msg["role"] == "user":
                            user_prompt = msg["content"]
                    
                    # Tenta com modelo de fallback
                    response = self._generate_with_model(system_prompt, user_prompt)
                    
                    # Restaura o modelo original
                    self.model_name = original_model
                    
                    if response is None:
                        raise ValueError("Falha ao gerar resposta com modelo de fallback")
                        
                    return response
                    
                except Exception as e2:
                    # Restaura o modelo original
                    self.model_name = original_model
                    raise ValueError(f"Erro no fallback: {e2}") from e2
            else:
                raise ValueError(f"Erro ao gerar resposta: {e}") from e

    def _generate_with_model(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """
        Gera resposta com um modelo específico.
        
        Args:
            system_prompt: Prompt de sistema
            user_prompt: Prompt do usuário
            
        Returns:
            String com resposta ou None se falhar
        """
        try:
            # Identifica o provedor baseado no nome do modelo
            provider = self._get_provider(self.model_name)
                    
            if not provider:
                logger.error(f"Provedor não identificado para modelo {self.model_name}")
                return None
                
            if provider == 'openai':
                response = self.openai_client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                return response.choices[0].message.content
                
            elif provider == 'openrouter' and self.openrouter_client:
                response = self.openrouter_client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                return response.choices[0].message.content
                
            elif provider == 'gemini' and self.gemini_model:
                response = self.gemini_model.generate_content(
                    f"{system_prompt}\n\n{user_prompt}",
                    generation_config={
                        "temperature": self.temperature,
                        "max_output_tokens": self.max_tokens
                    }
                )
                return response.text
                
            elif provider == 'tinyllama' and self.tinyllama_model:
                response = self.tinyllama_model.create_chat_completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                return response['choices'][0]['message']['content']
                
            elif provider == 'phi1' and self.phi1_model:
                # Formata o prompt para Phi-1
                full_prompt = ""
                if system_prompt:
                    full_prompt += f"<|system|>\n{system_prompt}\n"
                full_prompt += f"<|user|>\n{user_prompt}\n<|assistant|>\n"
                
                # Parâmetros para geração
                phi1_config = self.registry.get_provider_config('phi1')
                max_tokens = self.max_tokens or phi1_config.get('default_max_tokens', 100)
                stop = ["</s>", "<|user|>", "<|system|>", "<|assistant|>"]
                
                response = self.phi1_model(
                    full_prompt,
                    max_tokens=max_tokens,
                    temperature=self.temperature,
                    stop=stop
                )
                return response["choices"][0]["text"].strip()
                
            elif provider == 'deepseek_local' and self.deepseek_model:
                # Formata o prompt para DeepSeek Coder
                full_prompt = ""
                if system_prompt:
                    full_prompt += f" \n{system}\n Arbitro \n"
                full_prompt += f"<user>\n{user_prompt}\n</user>\n<assistant>\n"
                
                # Parâmetros para geração
                deepseek_config = self.registry.get_provider_config('deepseek_local')
                max_tokens = self.max_tokens or deepseek_config.get('default_max_tokens', 512)
                temperature = kwargs.get('temperature', self.temperature)
                stop = ["</assistant>", "<user>", " ", "</user>", " Arbitro "]
                
                response = self.deepseek_model(
                    full_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stop=stop
                )
                return response["choices"][0]["text"].strip()
                
            elif provider == 'phi3' and self.phi3_model:
                # Formata o prompt para Phi-3 Mini
                full_prompt = ""
                if system_prompt:
                    full_prompt += f"<|system|>\n{system}\n"
                full_prompt += f"<|user|>\n{user_prompt}\n<|assistant|>\n"
                
                # Parâmetros para geração
                phi3_config = self.registry.get_provider_config('phi3')
                max_tokens = self.max_tokens or phi3_config.get('default_max_tokens', 512)
                temperature = kwargs.get('temperature', self.temperature)
                stop = ["<|user|>", "<|system|>", "<|assistant|>"]
                
                response = self.phi3_model(
                    full_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stop=stop
                )
                return response["choices"][0]["text"].strip()
                
            # Se chegou aqui, o provedor não está configurado
            logger.error(f"Cliente não configurado para provedor {provider}")
            return None
            
        except Exception as e:
            logger.error(f"Erro ao gerar com {self.model_name}: {str(e)}")
            return None

    def _generate_openai(self, prompt: str, system: Optional[str] = None, **kwargs) -> Tuple[str, Dict[str, Any]]:
        """Gera resposta usando OpenAI."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        response = self.openai_client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=kwargs.get('temperature', self.temperature),
            max_tokens=kwargs.get('max_tokens', self.max_tokens)
        )
        
        return response.choices[0].message.content, {
            "model": response.model,
            "usage": response.usage.model_dump()
        }

    def _generate_gemini(self, prompt: str, system: Optional[str] = None, **kwargs) -> Tuple[str, Dict[str, Any]]:
        """Gera resposta usando Gemini."""
        if not self.gemini_model:
            raise ValueError("Gemini não configurado")
            
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        response = self.gemini_model.generate_content(
            messages,
            generation_config={
                "temperature": kwargs.get('temperature', self.temperature),
                "max_output_tokens": kwargs.get('max_tokens', self.max_tokens)
            }
        )
        
        return response.text, {
            "model": self.model_name,
            "usage": {}
        }

    def _generate_anthropic(self, prompt: str, system: Optional[str] = None, **kwargs) -> Tuple[str, Dict[str, Any]]:
        """Gera resposta usando Anthropic."""
        if not self.anthropic_client:
            raise ValueError("Anthropic não configurado")
            
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        response = self.anthropic_client.messages.create(
            model=self.model_name,
            messages=messages,
            temperature=kwargs.get('temperature', self.temperature),
            max_tokens=kwargs.get('max_tokens', self.max_tokens)
        )
        
        return response.content[0].text, {
            "model": response.model,
            "usage": {}
        }

    def _generate_tinyllama(self, prompt: str, system: Optional[str] = None, **kwargs) -> Tuple[str, Dict[str, Any]]:
        """Gera resposta usando TinyLLaMA."""
        if not self.tinyllama_model:
            raise ValueError("TinyLLaMA não configurado")
            
        try:
            # Formata o prompt
            full_prompt = ""
            if system:
                full_prompt += f"<|system|>\n{system} Arbitro \n"
            full_prompt += f"<|user|>\n{prompt} Arbitro \n<|assistant|>\n"
            
            # Parâmetros para geração
            tinyllama_config = self.registry.get_provider_config('tinyllama')
            max_tokens = kwargs.get('max_tokens', self.max_tokens) or tinyllama_config.get('default_max_tokens', 256)
            temperature = kwargs.get('temperature', self.temperature)
            stop = [" Arbitro ", "<|user|>", "<|system|>", "<|assistant|>"]
            
            # Usa apenas a API direta, que funciona em todas as versões
            response = self.tinyllama_model(
                full_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop
            )
            text = response["choices"][0]["text"].strip()
            
            # Tenta extrair JSON se presente
            try:
                if '{' in text and '}' in text:
                    start = text.find('{')
                    end = text.rfind('}') + 1
                    json_str = text[start:end]
                    
                    # Limpa o JSON
                    json_str = json_str.replace('\n', ' ').replace('\r', '')
                    while '  ' in json_str:
                        json_str = json_str.replace('  ', ' ')
                    
                    # Valida se é um JSON válido
                    json_data = json.loads(json_str)
                    text = json.dumps(json_data, ensure_ascii=False)
                else:
                    # Se não encontrou JSON, retorna texto normal
                    text = text
            except Exception as e:
                logger.error(f"Erro ao processar resposta JSON: {str(e)}")
                # Mantém o texto original em caso de erro
            
            return text, {
                "model": "tinyllama-1.1b",
                "usage": {
                    "prompt_tokens": len(full_prompt.split()),
                    "completion_tokens": len(text.split()),
                    "total_tokens": len(full_prompt.split()) + len(text.split())
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar resposta com TinyLLaMA: {str(e)}")
            # Retorna estrutura padrão em caso de erro
            text = json.dumps({
                "name": "Sistema Genérico",
                "description": "Sistema a ser especificado",
                "objectives": ["Definir objetivos específicos"],
                "requirements": ["Definir requisitos específicos"],
                "constraints": ["Definir restrições do sistema"]
            }, ensure_ascii=False)
            
            return text, {
                "model": "tinyllama-1.1b",
                "error": str(e),
                "usage": {
                    "prompt_tokens": len(prompt.split()),
                    "completion_tokens": len(text.split()),
                    "total_tokens": len(prompt.split()) + len(text.split())
                }
            }

    def _generate_phi1(self, prompt: str, system: Optional[str] = None, **kwargs) -> Tuple[str, Dict[str, Any]]:
        """Gera resposta usando Phi-1."""
        if not self.phi1_model:
            raise ValueError("Phi-1 não configurado")
            
        try:
            # Formata o prompt
            full_prompt = ""
            if system:
                full_prompt += f"<|system|>\n{system} Arbitro \n"
            full_prompt += f"<|user|>\n{prompt} Arbitro \n<|assistant|>\n"
            
            # Parâmetros para geração
            phi1_config = self.registry.get_provider_config('phi1')
            max_tokens = kwargs.get('max_tokens', self.max_tokens) or phi1_config.get('default_max_tokens', 100)
            temperature = kwargs.get('temperature', self.temperature)
            stop = [" Arbitro ", "<|user|>", "<|system|>", "<|assistant|>"]
            
            # Usa apenas a API direta, que funciona em todas as versões
            response = self.phi1_model(
                full_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop
            )
            text = response["choices"][0]["text"].strip()
            
            # Tenta extrair JSON se presente
            try:
                if '{' in text and '}' in text:
                    start = text.find('{')
                    end = text.rfind('}') + 1
                    json_str = text[start:end]
                    
                    # Limpa o JSON
                    json_str = json_str.replace('\n', ' ').replace('\r', '')
                    while '  ' in json_str:
                        json_str = json_str.replace('  ', ' ')
                    
                    # Valida se é um JSON válido
                    json_data = json.loads(json_str)
                    text = json.dumps(json_data, ensure_ascii=False)
                else:
                    # Se não encontrou JSON, retorna texto normal
                    text = text
            except Exception as e:
                logger.error(f"Erro ao processar resposta JSON: {str(e)}")
                # Mantém o texto original em caso de erro
            
            return text, {
                "model": "phi-1",
                "usage": {
                    "prompt_tokens": len(full_prompt.split()),
                    "completion_tokens": len(text.split()),
                    "total_tokens": len(full_prompt.split()) + len(text.split())
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar resposta com Phi-1: {str(e)}")
            # Retorna estrutura padrão em caso de erro
            text = json.dumps({
                "name": "Sistema Genérico",
                "description": "Sistema a ser especificado",
                "objectives": ["Definir objetivos específicos"],
                "requirements": ["Definir requisitos específicos"],
                "constraints": ["Definir restrições do sistema"]
            }, ensure_ascii=False)
            
            return text, {
                "model": "phi-1",
                "error": str(e),
                "usage": {
                    "prompt_tokens": len(prompt.split()),
                    "completion_tokens": len(text.split()),
                    "total_tokens": len(prompt.split()) + len(text.split())
                }
            }

    def _generate_deepseek(self, prompt: str, system: Optional[str] = None, **kwargs) -> Tuple[str, Dict[str, Any]]:
        """Gera resposta usando DeepSeek Coder."""
        if not self.deepseek_model:
            raise ValueError("DeepSeek Coder não configurado")
            
        try:
            # Formata o prompt para DeepSeek Coder
            full_prompt = ""
            if system:
                full_prompt += f" \n{system}\n Arbitro \n"

            full_prompt += f"<user>\n{prompt}\n</user>\n<assistant>\n"
            
            # Parâmetros para geração
            deepseek_config = self.registry.get_provider_config('deepseek_local')
            max_tokens = kwargs.get('max_tokens', self.max_tokens) or deepseek_config.get('default_max_tokens', 512)
            temperature = kwargs.get('temperature', self.temperature)
            stop = ["</assistant>", "<user>", " ", "</user>", " Arbitro "]
            
            # Usa apenas a API direta, que funciona em todas as versões
            response = self.deepseek_model(
                full_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop
            )
            text = response["choices"][0]["text"].strip()
            
            # Tenta extrair JSON se presente
            try:
                if '{' in text and '}' in text:
                    start = text.find('{')
                    end = text.rfind('}') + 1
                    json_str = text[start:end]
                    
                    # Limpa o JSON
                    json_str = json_str.replace('\n', ' ').replace('\r', '')
                    while '  ' in json_str:
                        json_str = json_str.replace('  ', ' ')
                    
                    # Valida se é um JSON válido
                    json_data = json.loads(json_str)
                    text = json.dumps(json_data, ensure_ascii=False)
                else:
                    # Se não encontrou JSON, retorna texto normal
                    text = text
            except Exception as e:
                logger.error(f"Erro ao processar resposta JSON: {str(e)}")
                # Mantém o texto original em caso de erro
            
            # Usa um ID de modelo consistente para metadados
            model_id = "deepseek-coder-local"
            
            return text, {
                "model": model_id,
                "usage": {
                    "prompt_tokens": len(full_prompt.split()),
                    "completion_tokens": len(text.split()),
                    "total_tokens": len(full_prompt.split()) + len(text.split())
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar resposta com DeepSeek Coder: {str(e)}")
            # Retorna estrutura padrão em caso de erro
            text = json.dumps({
                "name": "Sistema Genérico",
                "description": "Sistema a ser especificado",
                "objectives": ["Definir objetivos específicos"],
                "requirements": ["Definir requisitos específicos"],
                "constraints": ["Definir restrições do sistema"]
            }, ensure_ascii=False)
            
            # Usa um ID de modelo consistente para metadados
            model_id = "deepseek-coder-local"
            
            return text, {
                "model": model_id,
                "error": str(e),
                "usage": {
                    "prompt_tokens": len(prompt.split()),
                    "completion_tokens": len(text.split()),
                    "total_tokens": len(prompt.split()) + len(text.split())
                }
            }

    def _generate_phi3(self, prompt: str, system: Optional[str] = None, **kwargs) -> Tuple[str, Dict[str, Any]]:
        """Gera resposta usando Phi-3 Mini."""
        if not self.phi3_model:
            raise ValueError("Phi-3 Mini não configurado")
            
        try:
            # Formata o prompt para Phi-3 Mini
            full_prompt = ""
            if system:
                full_prompt += f"<|system|>\n{system}\n"
            full_prompt += f"<|user|>\n{prompt}\n<|assistant|>\n"
            
            # Parâmetros para geração
            phi3_config = self.registry.get_provider_config('phi3')
            max_tokens = kwargs.get('max_tokens', self.max_tokens) or phi3_config.get('default_max_tokens', 512)
            temperature = kwargs.get('temperature', self.temperature)
            stop = ["<|user|>", "<|system|>", "<|assistant|>"]
            
            # Usa apenas a API direta, que funciona em todas as versões
            response = self.phi3_model(
                full_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop
            )
            text = response["choices"][0]["text"].strip()
            
            # Tenta extrair JSON se presente
            try:
                if '{' in text and '}' in text:
                    start = text.find('{')
                    end = text.rfind('}') + 1
                    json_str = text[start:end]
                    
                    # Limpa o JSON
                    json_str = json_str.replace('\n', ' ').replace('\r', '')
                    while '  ' in json_str:
                        json_str = json_str.replace('  ', ' ')
                    
                    # Valida se é um JSON válido
                    json_data = json.loads(json_str)
                    text = json.dumps(json_data, ensure_ascii=False)
                else:
                    # Se não encontrou JSON, retorna texto normal
                    text = text
            except Exception as e:
                logger.error(f"Erro ao processar resposta JSON: {str(e)}")
                # Mantém o texto original em caso de erro
            
            # Usa nome padronizado do modelo
            model_id = "phi3-mini"
            
            return text, {
                "model": model_id,
                "usage": {
                    "prompt_tokens": len(full_prompt.split()),
                    "completion_tokens": len(text.split()),
                    "total_tokens": len(full_prompt.split()) + len(text.split())
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar resposta com Phi-3 Mini: {str(e)}")
            # Retorna estrutura padrão em caso de erro
            text = json.dumps({
                "name": "Sistema Genérico",
                "description": "Sistema a ser especificado",
                "objectives": ["Definir objetivos específicos"],
                "requirements": ["Definir requisitos específicos"],
                "constraints": ["Definir restrições do sistema"]
            }, ensure_ascii=False)
            
            # Usa nome padronizado do modelo
            model_id = "phi3-mini"
            
            return text, {
                "model": model_id,
                "error": str(e),
                "usage": {
                    "prompt_tokens": len(prompt.split()),
                    "completion_tokens": len(text.split()),
                    "total_tokens": len(prompt.split()) + len(text.split())
                }
            }

class ModelRegistry:
    def __init__(self, config_path: Optional[str] = None):
        base_dir = Path(__file__).resolve().parent.parent
        config_file = config_path or os.path.join(base_dir, "configs", "kernel.yaml")

        with open(config_file, "r", encoding="utf-8") as f:
            full_config = yaml.safe_load(f)
            self.config = full_config["models"]
            self.providers = self.config["providers"]

    def get_default_model(self) -> str:
        return self.config['defaults']['model']

    def get_provider_by_model_id(self, model_id: str) -> Optional[Dict[str, Any]]:
        for provider in self.providers:
            for pattern in provider.get('prefix_patterns', []):
                if model_id.startswith(pattern):
                    return provider
        return None

    def get_model_config(self, model_id: str) -> Optional[Dict[str, Any]]:
        provider = self.get_provider_by_model_id(model_id)
        if not provider:
            return None

        for name in provider.get('models', []):
            if name == model_id:
                return {
                    'provider': provider['name'],
                    'model_id': model_id,
                    'config': provider
                }
        return None

    def list_all_models(self) -> List[str]:
        return [model for p in self.providers for model in p.get('models', [])]

    def list_providers(self) -> List[str]:
        return [p['name'] for p in self.providers]

    def get_env_var_for_provider(self, provider_name: str) -> Optional[str]:
        for p in self.providers:
            if p['name'] == provider_name:
                return p.get('env_key')
        return None

    def get_provider_name(self, model_id: str) -> str:
        """
        Obtém o nome do provedor com base no ID do modelo.
        
        Args:
            model_id: ID do modelo
            
        Returns:
            Nome do provedor ou 'openai' como fallback
        """
        for provider in self.providers:
            name = provider.get('name')
            for pattern in provider.get('prefix_patterns', []):
                if model_id.startswith(pattern):
                    return name
        
        # Se não encontrou correspondência, retorna openai como fallback
        return 'openai'

    def get_provider_config(self, provider_name: str) -> Dict[str, Any]:
        for p in self.providers:
            if p['name'] == provider_name:
                return p
        return {}

    def get_available_models(self) -> Dict[str, List[str]]:
        return {p['name']: p.get('models', []) for p in self.providers}

    def resolve_model_config(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        model_name = model_id or self.get_default_model()
        model_config = self.get_model_config(model_name)
        if not model_config:
            raise ValueError(f"Modelo '{model_name}' não encontrado na configuração")
        return model_config

    def get_env_vars(self) -> Dict[str, str]:
        return self.config.get('env_vars', {})

    class ModelProvider(str, Enum):
        """Provedores de modelos suportados."""
        OPENAI = "openai"
        OPENROUTER = "openrouter"
        GEMINI = "gemini"
        TINYLLAMA = "tinyllama"
        PHI1 = "phi1"
        DEEPSEEK_LOCAL = "deepseek_local"
        PHI3 = "phi3"

    def get_defaults(self) -> Dict[str, Any]:
        return self.config.get('defaults', {})

# Função para verificar e baixar modelos
class ModelDownloader:
    @staticmethod
    def verify_and_download_models():
        config = load_config()
        for provider in config['providers']:
            url = provider.get('url')
            if url:
                model_name = provider['model']
                ModelDownloader.download_model(model_name, url)

    @staticmethod
    def download_model(model_name, url):
        model_path = os.path.join(ModelDownloader.MODEL_DIR, f"{model_name}.gguf")
        if not ModelDownloader.is_model_available(model_name):
            print(f"📥 Baixando modelo {model_name}...")
            os.makedirs(ModelDownloader.MODEL_DIR, exist_ok=True)
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                with open(model_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"✅ Modelo {model_name} baixado com sucesso!")
            else:
                print(f"❌ Falha ao baixar o modelo {model_name}. Código de status: {response.status_code}")
        else:
            print(f"✅ Modelo {model_name} já está disponível.")

    @staticmethod
    def is_model_available(model_name: str) -> bool:
        model_path = os.path.join(ModelDownloader.MODEL_DIR, f"{model_name}.gguf")
        return os.path.exists(model_path) and os.path.getsize(model_path) >= 1000000