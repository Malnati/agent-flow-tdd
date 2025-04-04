"""
Gerenciador de modelos de IA com suporte a múltiplos provedores e fallback automático.
"""
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import os
import json
import time

import google.generativeai as genai
from pydantic import BaseModel
from openai import OpenAI
from anthropic import Anthropic

from src.core.kernel import get_env_var
from src.core.logger import get_logger

logger = get_logger(__name__)


class ModelProvider(str, Enum):
    """Provedores de modelos suportados."""
    OPENAI = "openai"
    OPENROUTER = "openrouter"
    GEMINI = "gemini"


class ModelConfig(BaseModel):
    """Configuração de um modelo."""
    provider: ModelProvider
    model_id: str
    api_key: str
    timeout: int = 30
    max_retries: int = 3
    temperature: float = 0.7
    max_tokens: Optional[int] = None


class ModelManager:
    """Gerenciador de modelos de IA."""

    def __init__(self, model_name: Optional[str] = None):
        """
        Inicializa o gerenciador com configurações do modelo.
        
        Args:
            model_name: Nome do modelo a ser usado (opcional)
        """
        self.model_name = model_name or get_env_var('DEFAULT_MODEL', 'gpt-4')
        self.elevation_model = get_env_var('ELEVATION_MODEL', 'gpt-4')
        
        # Configurações de retry e timeout
        self.max_retries = int(get_env_var('MAX_RETRIES', '3'))
        self.timeout = int(get_env_var('MODEL_TIMEOUT', '120'))
        
        # Configuração de fallback
        self.fallback_enabled = get_env_var('FALLBACK_ENABLED', 'true').lower() == 'true'
        
        # Cache de respostas
        self.cache_enabled = get_env_var('CACHE_ENABLED', 'true').lower() == 'true'
        self.cache_ttl = int(get_env_var('CACHE_TTL', '3600'))  # 1 hora
        self.cache_dir = get_env_var('CACHE_DIR', 'cache')
        self._setup_cache()
        
        # Inicializa clientes
        self._setup_clients()
        
        # Configurações padrão
        self.temperature = 0.7
        self.max_tokens = None
        
        logger.info(f"ModelManager inicializado com modelo {self.model_name}")

    def configure(self, model: Optional[str] = None, temperature: float = 0.7, max_tokens: Optional[int] = None) -> None:
        """
        Configura parâmetros do modelo.
        
        Args:
            model: Nome do modelo a ser usado
            temperature: Temperatura para geração (0.0 a 1.0)
            max_tokens: Número máximo de tokens na resposta
        """
        if model:
            self.model_name = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        logger.info(f"ModelManager configurado: model={self.model_name}, temperature={self.temperature}, max_tokens={self.max_tokens}")

    def _setup_cache(self) -> None:
        """Configura diretório de cache"""
        if self.cache_enabled:
            os.makedirs(self.cache_dir, exist_ok=True)
            
    def _setup_clients(self) -> None:
        """Inicializa clientes para diferentes provedores"""
        # OpenAI
        self.openai_client = OpenAI(
            api_key=get_env_var('OPENAI_API_KEY'),
            timeout=self.timeout
        )
        
        # OpenRouter (opcional)
        openrouter_key = get_env_var('OPENROUTER_KEY')
        if openrouter_key:
            self.openrouter_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_key,
                timeout=self.timeout
            )
        else:
            self.openrouter_client = None
            
        # Gemini (opcional)
        gemini_key = get_env_var('GEMINI_KEY') 
        if gemini_key:
            genai.configure(api_key=gemini_key)
            self.gemini_model = genai.GenerativeModel('gemini-pro')
        else:
            self.gemini_model = None
            
        # Anthropic (opcional)
        anthropic_key = get_env_var('ANTHROPIC_KEY')
        if anthropic_key:
            self.anthropic_client = Anthropic(api_key=anthropic_key)
        else:
            self.anthropic_client = None
            
    def _get_cache_key(self, prompt: str, model: str) -> str:
        """
        Gera chave única para cache.
        
        Args:
            prompt: Prompt para o modelo
            model: Nome do modelo
            
        Returns:
            String com a chave de cache
        """
        import hashlib
        key = f"{prompt}:{model}"
        return hashlib.md5(key.encode()).hexdigest()
        
    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        """
        Busca resposta em cache.
        
        Args:
            cache_key: Chave do cache
            
        Returns:
            Resposta em cache ou None
        """
        if not self.cache_enabled:
            return None
            
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        if not os.path.exists(cache_file):
            return None
            
        # Verifica TTL
        mtime = os.path.getmtime(cache_file)
        if time.time() - mtime > self.cache_ttl:
            os.remove(cache_file)
            return None
            
        with open(cache_file) as f:
            return json.load(f)
            
    def _save_to_cache(self, cache_key: str, response: Dict[str, Any]) -> None:
        """
        Salva resposta em cache.
        
        Args:
            cache_key: Chave do cache
            response: Resposta a ser cacheada
        """
        if not self.cache_enabled:
            return
            
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        with open(cache_file, 'w') as f:
            json.dump(response, f)
            
    def _get_provider(self, model: str) -> str:
        """
        Identifica o provedor com base no nome do modelo.
        
        Args:
            model: Nome do modelo
            
        Returns:
            String com o nome do provedor
        """
        if model.startswith(('gpt-', 'text-')):
            return 'openai'
        elif model.startswith('gemini-'):
            return 'gemini'
        elif model.startswith('claude-'):
            return 'anthropic'
        elif model.startswith('deepseek-'):
            return 'openrouter'
        else:
            return 'openai'  # default
            
    def _generate_with_provider(
        self, 
        prompt: str,
        model: str,
        provider: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Gera resposta usando provedor específico.
        
        Args:
            prompt: Prompt para o modelo
            model: Nome do modelo
            provider: Nome do provedor
            temperature: Temperatura para geração
            max_tokens: Número máximo de tokens
            stop: Lista de strings para parar geração
            
        Returns:
            Tupla com (texto gerado, metadados)
        """
        try:
            if provider == 'openai':
                response = self.openai_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stop=stop
                )
                return response.choices[0].message.content, {
                    "model": model,
                    "provider": "openai",
                    "finish_reason": response.choices[0].finish_reason,
                    "created": response.created,
                    "id": response.id
                }
                
            elif provider == 'gemini':
                response = self.gemini_model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": temperature,
                        "max_output_tokens": max_tokens,
                        "stop_sequences": stop
                    }
                )
                return response.text, {
                    "model": model,
                    "provider": "gemini",
                    "finish_reason": "stop",
                    "created": int(time.time()),
                    "id": None
                }
                
            elif provider == 'anthropic':
                response = self.anthropic_client.messages.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stop_sequences=stop
                )
                return response.content[0].text, {
                    "model": model,
                    "provider": "anthropic",
                    "finish_reason": "stop",
                    "created": int(time.time()),
                    "id": response.id
                }
                
            elif provider == 'openrouter':
                response = self.openrouter_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stop=stop
                )
                return response.choices[0].message.content, {
                    "model": model,
                    "provider": "openrouter",
                    "finish_reason": response.choices[0].finish_reason,
                    "created": response.created,
                    "id": response.id
                }
                
            else:
                raise ValueError(f"Provedor não suportado: {provider}")
                
        except Exception as e:
            logger.error(f"Erro ao gerar com {provider}: {str(e)}")
            raise
            
    def generate(
        self, 
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        use_cache: bool = True
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Gera resposta para um prompt.
        
        Args:
            prompt: Prompt para o modelo
            model: Nome do modelo (opcional)
            temperature: Temperatura para geração
            max_tokens: Número máximo de tokens
            stop: Lista de strings para parar geração
            use_cache: Se deve usar cache
            
        Returns:
            Tupla com (texto gerado, metadados)
        """
        model = model or self.model_name
        
        # Tenta cache primeiro
        if use_cache and self.cache_enabled:
            cache_key = self._get_cache_key(prompt, model)
            cached = self._get_cached_response(cache_key)
            if cached:
                logger.info(f"Usando resposta em cache para {model}")
                return cached["text"], cached["metadata"]
                
        # Identifica provedor
        provider = self._get_provider(model)
        
        # Tenta gerar resposta com retry
        for attempt in range(self.max_retries):
            try:
                text, metadata = self._generate_with_provider(
                    prompt=prompt,
                    model=model,
                    provider=provider,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stop=stop
                )
                
                # Salva em cache
                if use_cache and self.cache_enabled:
                    self._save_to_cache(cache_key, {
                        "text": text,
                        "metadata": metadata
                    })
                    
                return text, metadata
                
            except Exception as e:
                logger.warning(
                    f"Tentativa {attempt + 1} falhou: {str(e)}"
                )
                if attempt == self.max_retries - 1:
                    if self.fallback_enabled and model != self.elevation_model:
                        logger.info(
                            f"Tentando fallback para {self.elevation_model}"
                        )
                        return self.generate(
                            prompt=prompt,
                            model=self.elevation_model,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            stop=stop,
                            use_cache=use_cache
                        )
                    else:
                        raise
                time.sleep(2 ** attempt)  # Exponential backoff 