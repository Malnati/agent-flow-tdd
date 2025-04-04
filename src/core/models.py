"""
Gerenciador de modelos de IA com suporte a múltiplos provedores e fallback automático.
"""
from enum import Enum
from typing import Any, Dict, Optional, Tuple
import os
import json
import time
import yaml
from pathlib import Path

import google.generativeai as genai
from pydantic import BaseModel
from openai import OpenAI
from anthropic import Anthropic

from src.core.kernel import get_env_var
from src.core.logger import get_logger

logger = get_logger(__name__)

def load_config() -> Dict[str, Any]:
    """
    Carrega as configurações do model manager do arquivo YAML.
    
    Returns:
        Dict com as configurações
    """
    base_dir = Path(__file__).resolve().parent.parent.parent
    config_path = os.path.join(base_dir, 'src', 'configs', 'models.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

# Carrega configurações
CONFIG = load_config()

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
    timeout: int = CONFIG['defaults']['timeout']
    max_retries: int = CONFIG['defaults']['max_retries']
    temperature: float = CONFIG['defaults']['temperature']
    max_tokens: Optional[int] = CONFIG['defaults']['max_tokens']


class ModelManager:
    """Gerenciador de modelos de IA."""

    def __init__(self, model_name: Optional[str] = None):
        """
        Inicializa o gerenciador com configurações do modelo.
        
        Args:
            model_name: Nome do modelo a ser usado (opcional)
        """
        env = CONFIG['env_vars']
        self.model_name = model_name or get_env_var(env['default_model'], CONFIG['defaults']['model'])
        self.elevation_model = get_env_var(env['elevation_model'], CONFIG['defaults']['elevation_model'])
        
        # Configurações de retry e timeout
        self.max_retries = int(get_env_var(env['max_retries'], str(CONFIG['defaults']['max_retries'])))
        self.timeout = int(get_env_var(env['model_timeout'], str(CONFIG['defaults']['timeout'])))
        
        # Configuração de fallback
        self.fallback_enabled = get_env_var(env['fallback_enabled'], str(CONFIG['fallback']['enabled'])).lower() == 'true'
        
        # Cache de respostas
        self.cache_enabled = get_env_var(env['cache_enabled'], str(CONFIG['cache']['enabled'])).lower() == 'true'
        self.cache_ttl = int(get_env_var(env['cache_ttl'], str(CONFIG['cache']['ttl'])))
        self.cache_dir = get_env_var(env['cache_dir'], CONFIG['cache']['directory'])
        self._setup_cache()
        
        # Inicializa clientes
        self._setup_clients()
        
        # Configurações padrão
        self.temperature = CONFIG['defaults']['temperature']
        self.max_tokens = CONFIG['defaults']['max_tokens']
        
        logger.info(f"ModelManager inicializado com modelo {self.model_name}")

    def configure(self, model: Optional[str] = None, temperature: float = CONFIG['defaults']['temperature'], max_tokens: Optional[int] = None) -> None:
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
        env = CONFIG['env_vars']
        
        # OpenAI
        self.openai_client = OpenAI(
            api_key=get_env_var(env['openai_key']),
            timeout=self.timeout
        )
        
        # OpenRouter (opcional)
        openrouter_key = get_env_var(env['openrouter_key'])
        if openrouter_key:
            self.openrouter_client = OpenAI(
                base_url=CONFIG['providers']['openrouter']['base_url'],
                api_key=openrouter_key,
                timeout=self.timeout
            )
        else:
            self.openrouter_client = None
            
        # Gemini (opcional)
        gemini_key = get_env_var(env['gemini_key'])
        if gemini_key:
            genai.configure(api_key=gemini_key)
            self.gemini_model = genai.GenerativeModel(CONFIG['providers']['gemini']['default_model'])
        else:
            self.gemini_model = None
            
        # Anthropic (opcional)
        anthropic_key = get_env_var(env['anthropic_key'])
        if anthropic_key:
            self.anthropic_client = Anthropic(api_key=anthropic_key)
        else:
            self.anthropic_client = None
            
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
            
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        if not os.path.exists(cache_file):
            return None
            
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
                
            # Verifica TTL
            if time.time() - cache_data['timestamp'] > self.cache_ttl:
                os.remove(cache_file)
                return None
                
            return cache_data['response'], cache_data['metadata']
            
        except Exception as e:
            logger.error(f"Erro ao ler cache: {str(e)}")
            return None
            
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
            cache_data = {
                'response': response,
                'metadata': metadata,
                'timestamp': time.time()
            }
            
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
                
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
        providers_config = CONFIG['providers']
        
        # Verifica cada provedor
        for provider, config in providers_config.items():
            if 'prefix_patterns' in config:
                for prefix in config['prefix_patterns']:
                    if model.startswith(prefix):
                        return provider
                        
        # Retorna OpenAI como default
        return 'openai'

    def _get_provider_config(self, provider: str) -> Dict[str, Any]:
        """
        Obtém configurações específicas do provedor.
        
        Args:
            provider: Nome do provedor
            
        Returns:
            Dict com configurações do provedor
        """
        return CONFIG['providers'].get(provider, {})

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
        """
        provider_config = self._get_provider_config(provider)
        
        try:
            if provider == 'openai':
                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})
                
                response = self.openai_client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    **kwargs
                )
                return response.choices[0].message.content, {
                    "model": self.model_name,
                    "provider": provider,
                    "status": "success"
                }
                
            elif provider == 'openrouter' and self.openrouter_client:
                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})
                
                response = self.openrouter_client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    **kwargs
                )
                return response.choices[0].message.content, {
                    "model": self.model_name,
                    "provider": provider,
                    "status": "success"
                }
                
            elif provider == 'gemini' and self.gemini_model:
                response = self.gemini_model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=self.temperature,
                        max_output_tokens=self.max_tokens or provider_config.get('default_max_tokens', 1024),
                        **kwargs
                    )
                )
                return response.text, {
                    "model": provider_config['default_model'],
                    "provider": provider,
                    "status": "success"
                }
                
            elif provider == 'anthropic' and self.anthropic_client:
                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})
                
                response = self.anthropic_client.messages.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens or provider_config.get('default_max_tokens', 1024),
                    **kwargs
                )
                return response.content[0].text, {
                    "model": self.model_name,
                    "provider": provider,
                    "status": "success"
                }
                
            else:
                raise ValueError(f"Provedor {provider} não disponível")
                
        except Exception as e:
            logger.error(f"Erro ao gerar com provedor {provider}: {str(e)}")
            return "", {
                "error": str(e),
                "model": self.model_name,
                "provider": provider,
                "status": "error"
            }

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        use_cache: bool = True,
        **kwargs
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Gera resposta para um prompt.
        
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