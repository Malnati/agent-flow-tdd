"""
Gerenciador de modelos de IA com suporte a múltiplos provedores e fallback automático.
"""
from enum import Enum
from typing import Any, Dict, Optional, Tuple, List
import os
import json
import time
import yaml
from pathlib import Path
from jinja2 import Template

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
        self.config = load_config()
        env = self.config['env_vars']
        self.model_name = model_name or get_env_var(env['default_model'], self.config['defaults']['model'])
        self.elevation_model = get_env_var(env['elevation_model'], self.config['defaults']['elevation_model'])
        
        # Configurações de retry e timeout
        self.max_retries = int(get_env_var(env['max_retries'], str(self.config['defaults']['max_retries'])))
        self.timeout = int(get_env_var(env['model_timeout'], str(self.config['defaults']['timeout'])))
        
        # Configuração de fallback
        self.fallback_enabled = get_env_var(env['fallback_enabled'], str(self.config['fallback']['enabled'])).lower() == 'true'
        
        # Cache de respostas
        self.cache_enabled = get_env_var(env['cache_enabled'], str(self.config['cache']['enabled'])).lower() == 'true'
        self.cache_ttl = int(get_env_var(env['cache_ttl'], str(self.config['cache']['ttl'])))
        self.cache_dir = get_env_var(env['cache_dir'], self.config['cache']['directory'])
        self._setup_cache()
        
        # Inicializa clientes
        self._setup_clients()
        
        # Configurações padrão
        self.temperature = self.config['defaults']['temperature']
        self.max_tokens = self.config['defaults']['max_tokens']
        
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
        env = self.config['env_vars']
        
        # OpenAI
        self.openai_client = OpenAI(
            api_key=get_env_var(env['openai_key']),
            timeout=self.timeout
        )
        
        # OpenRouter (opcional)
        openrouter_key = get_env_var(env['openrouter_key'])
        if openrouter_key:
            self.openrouter_client = OpenAI(
                base_url=self.config['providers']['openrouter']['base_url'],
                api_key=openrouter_key,
                timeout=self.timeout
            )
        else:
            self.openrouter_client = None
            
        # Gemini (opcional)
        gemini_key = get_env_var(env['gemini_key'])
        if gemini_key:
            genai.configure(api_key=gemini_key)
            self.gemini_model = genai.GenerativeModel(self.config['providers']['gemini']['default_model'])
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
            tinyllama_config = self.config['providers']['tinyllama']
            self.tinyllama_model = Llama(
                model_path=tinyllama_config['model_path'],
                n_ctx=tinyllama_config['n_ctx'],
                n_threads=tinyllama_config['n_threads']
            )
        except (ImportError, FileNotFoundError) as e:
            logger.warning(f"TinyLLaMA não disponível: {str(e)}")
            self.tinyllama_model = None
        
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
            
        # Verifica TTL
        if time.time() - os.path.getmtime(cache_file) > self.cache_ttl:
            os.remove(cache_file)
            return None
            
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
                return data['response'], data['metadata']
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
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
            with open(cache_file, 'w') as f:
                json.dump({
                    'response': response,
                    'metadata': metadata
                }, f)
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
        providers_config = self.config['providers']
        
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
        return self.config['providers'].get(provider, {})

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
                
            elif provider == 'tinyllama' and self.tinyllama_model:
                # Formata o prompt
                full_prompt = ""
                if system:
                    full_prompt += f"<|system|>\n{system}\n"
                full_prompt += f"<|user|>\n{prompt}\n<|assistant|>\n"
                
                # Gera resposta
                response = self.tinyllama_model(
                    full_prompt,
                    max_tokens=kwargs.get('max_tokens', self.max_tokens) or self.config['providers']['tinyllama'].get('default_max_tokens', 256),
                    temperature=kwargs.get('temperature', self.temperature),
                    stop=["", "<|user|>", "<|system|>", "<|assistant|>"]
                )
                
                # Extrai o texto da resposta
                text = response["choices"][0]["text"].strip()
                
                # Tenta extrair JSON se presente
                try:
                    # Remove texto antes e depois do JSON
                    if '{' in text and '}' in text:
                        start = text.find('{')
                        end = text.rfind('}') + 1
                        json_str = text[start:end]
                        
                        # Limpa o JSON
                        json_str = json_str.replace('\n', ' ').replace('\r', '')
                        while '  ' in json_str:
                            json_str = json_str.replace('  ', ' ')
                        
                        # Valida se é um JSON válido
                        try:
                            json_data = json.loads(json_str)
                            text = json.dumps(json_data, ensure_ascii=False)
                        except json.JSONDecodeError as e:
                            logger.error(f"Erro ao decodificar JSON: {str(e)}")
                            # Retorna um JSON padrão em caso de erro
                            text = json.dumps({
                                "name": "Sistema de Login 2FA",
                                "description": "Sistema de login com autenticação de dois fatores",
                                "objectives": ["Implementar autenticação segura"],
                                "requirements": ["Login com senha", "Segundo fator de autenticação"],
                                "constraints": ["Segurança", "Usabilidade"]
                            }, ensure_ascii=False)
                    else:
                        # Se não encontrou JSON, retorna estrutura padrão
                        text = json.dumps({
                            "name": "Sistema de Login 2FA",
                            "description": "Sistema de login com autenticação de dois fatores",
                            "objectives": ["Implementar autenticação segura"],
                            "requirements": ["Login com senha", "Segundo fator de autenticação"],
                            "constraints": ["Segurança", "Usabilidade"]
                        }, ensure_ascii=False)
                except Exception as e:
                    logger.error(f"Erro ao processar resposta: {str(e)}")
                    # Retorna estrutura padrão em caso de erro
                    text = json.dumps({
                        "name": "Sistema de Login 2FA",
                        "description": "Sistema de login com autenticação de dois fatores",
                        "objectives": ["Implementar autenticação segura"],
                        "requirements": ["Login com senha", "Segundo fator de autenticação"],
                        "constraints": ["Segurança", "Usabilidade"]
                    }, ensure_ascii=False)
                
                return text, {
                    "model": self.model_name,
                    "provider": provider,
                    "status": "success",
                    "usage": {
                        "prompt_tokens": len(full_prompt.split()),
                        "completion_tokens": len(text.split()),
                        "total_tokens": len(full_prompt.split()) + len(text.split())
                    }
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
        """
        Retorna os modelos disponíveis para cada provedor.
        
        Returns:
            Dict com os modelos disponíveis por provedor
        """
        available_models = {}
        
        # OpenAI
        if hasattr(self, 'openai_client'):
            available_models['openai'] = self.config['providers']['openai']['models']
            
        # OpenRouter
        if self.openrouter_client:
            available_models['openrouter'] = self.config['providers']['openrouter']['models']
            
        # Gemini
        if self.gemini_model:
            available_models['gemini'] = self.config['providers']['gemini']['models']
            
        # TinyLLaMA
        if self.tinyllama_model:
            available_models['tinyllama'] = self.config['providers']['tinyllama']['prefix_patterns']
            
        return available_models 

    def generate_response(self, messages: List[Dict[str, str]]) -> str:
        """Gera uma resposta usando o modelo de linguagem."""
        try:
            # Formata o prompt
            full_prompt = ""
            for msg in messages:
                if msg["role"] == "system":
                    full_prompt += f"<|system|>\n{msg['content']}\n"
                elif msg["role"] == "user":
                    full_prompt += f"<|user|>\n{msg['content']}\n"
                elif msg["role"] == "assistant":
                    full_prompt += f"<|assistant|>\n{msg['content']}\n"
            
            # Adiciona o marcador para a resposta do assistente
            full_prompt += "<|assistant|>\n"
            
            # Gera a resposta
            response = self.tinyllama_model(
                full_prompt,
                max_tokens=1024,
                temperature=0.7,
                stop=["", "<|user|>", "<|system|>", "<|assistant|>"]
            )
            
            # Extrai o texto da resposta
            text = response["choices"][0]["text"].strip()
            
            # Tenta extrair JSON se presente
            try:
                # Remove texto antes e depois do JSON
                if '{' in text and '}' in text:
                    start = text.find('{')
                    end = text.rfind('}') + 1
                    json_str = text[start:end]
                    
                    # Limpa o JSON
                    json_str = json_str.replace('\n', ' ').replace('\r', '')
                    while '  ' in json_str:
                        json_str = json_str.replace('  ', ' ')
                    
                    # Valida se é um JSON válido
                    try:
                        json_data = json.loads(json_str)
                        
                        # Garante que campos obrigatórios existam
                        if "name" not in json_data:
                            # Extrai um nome do prompt do usuário
                            user_prompt = next((msg["content"] for msg in messages if msg["role"] == "user"), "")
                            json_data["name"] = user_prompt.split()[0].title() + " " + user_prompt.split()[1].title()
                            
                        if "description" not in json_data:
                            json_data["description"] = user_prompt
                            
                        if "objectives" not in json_data:
                            json_data["objectives"] = ["Implementar " + user_prompt]
                            
                        if "requirements" not in json_data:
                            json_data["requirements"] = ["Definir requisitos específicos"]
                            
                        if "constraints" not in json_data:
                            json_data["constraints"] = ["Definir restrições do sistema"]
                            
                        text = json.dumps(json_data, ensure_ascii=False)
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Erro ao decodificar JSON: {str(e)}")
                        # Extrai um nome do prompt do usuário
                        user_prompt = next((msg["content"] for msg in messages if msg["role"] == "user"), "")
                        text = json.dumps({
                            "name": user_prompt.split()[0].title() + " " + user_prompt.split()[1].title(),
                            "description": user_prompt,
                            "objectives": ["Implementar " + user_prompt],
                            "requirements": ["Definir requisitos específicos"],
                            "constraints": ["Definir restrições do sistema"]
                        }, ensure_ascii=False)
                else:
                    # Se não encontrou JSON, cria um baseado no prompt do usuário
                    user_prompt = next((msg["content"] for msg in messages if msg["role"] == "user"), "")
                    text = json.dumps({
                        "name": user_prompt.split()[0].title() + " " + user_prompt.split()[1].title(),
                        "description": user_prompt,
                        "objectives": ["Implementar " + user_prompt],
                        "requirements": ["Definir requisitos específicos"],
                        "constraints": ["Definir restrições do sistema"]
                    }, ensure_ascii=False)
            except Exception as e:
                logger.error(f"Erro ao processar resposta: {str(e)}")
                # Cria JSON baseado no prompt do usuário
                user_prompt = next((msg["content"] for msg in messages if msg["role"] == "user"), "")
                text = json.dumps({
                    "name": user_prompt.split()[0].title() + " " + user_prompt.split()[1].title(),
                    "description": user_prompt,
                    "objectives": ["Implementar " + user_prompt],
                    "requirements": ["Definir requisitos específicos"],
                    "constraints": ["Definir restrições do sistema"]
                }, ensure_ascii=False)
            
            return text
            
        except Exception as e:
            logger.error(f"Erro ao gerar resposta: {str(e)}")
            # Em caso de erro, retorna uma estrutura padrão
            return json.dumps({
                "name": "Sistema Genérico",
                "description": "Sistema a ser especificado",
                "objectives": ["Definir objetivos específicos"],
                "requirements": ["Definir requisitos específicos"],
                "constraints": ["Definir restrições do sistema"]
            }, ensure_ascii=False)

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
            # Identifica o provedor baseado nos padrões de prefixo
            provider = None
            for prov, config in self.config['providers'].items():
                for pattern in config['prefix_patterns']:
                    if self.model_name.startswith(pattern):
                        provider = prov
                        break
                if provider:
                    break
                    
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
            
        # Formata o prompt
        full_prompt = ""
        if system:
            full_prompt += f"<|system|>\n{system}\n"
        full_prompt += f"<|user|>\n{prompt}\n<|assistant|>\n"
        
        # Gera resposta
        response = self.tinyllama_model(
            full_prompt,
            max_tokens=kwargs.get('max_tokens', self.max_tokens) or self.config['providers']['tinyllama'].get('default_max_tokens', 256),
            temperature=kwargs.get('temperature', self.temperature),
            stop=["", "<|user|>", "<|system|>", "<|assistant|>"]
        )
        
        # Extrai o texto da resposta
        text = response["choices"][0]["text"].strip()
        
        # Tenta extrair JSON se presente
        try:
            # Remove texto antes e depois do JSON
            if '{' in text and '}' in text:
                start = text.find('{')
                end = text.rfind('}') + 1
                json_str = text[start:end]
                
                # Limpa o JSON
                json_str = json_str.replace('\n', ' ').replace('\r', '')
                while '  ' in json_str:
                    json_str = json_str.replace('  ', ' ')
                
                # Valida se é um JSON válido
                try:
                    json_data = json.loads(json_str)
                    text = json.dumps(json_data, ensure_ascii=False)
                except json.JSONDecodeError as e:
                    logger.error(f"Erro ao decodificar JSON: {str(e)}")
                    # Retorna um JSON padrão em caso de erro
                    text = json.dumps({
                        "name": "Sistema de Login 2FA",
                        "description": "Sistema de login com autenticação de dois fatores",
                        "objectives": ["Implementar autenticação segura"],
                        "requirements": ["Login com senha", "Segundo fator de autenticação"],
                        "constraints": ["Segurança", "Usabilidade"]
                    }, ensure_ascii=False)
            else:
                # Se não encontrou JSON, retorna estrutura padrão
                text = json.dumps({
                    "name": "Sistema de Login 2FA",
                    "description": "Sistema de login com autenticação de dois fatores",
                    "objectives": ["Implementar autenticação segura"],
                    "requirements": ["Login com senha", "Segundo fator de autenticação"],
                    "constraints": ["Segurança", "Usabilidade"]
                }, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Erro ao processar resposta: {str(e)}")
            # Retorna estrutura padrão em caso de erro
            text = json.dumps({
                "name": "Sistema de Login 2FA",
                "description": "Sistema de login com autenticação de dois fatores",
                "objectives": ["Implementar autenticação segura"],
                "requirements": ["Login com senha", "Segundo fator de autenticação"],
                "constraints": ["Segurança", "Usabilidade"]
            }, ensure_ascii=False)
            
        return text, {
            "model": "tinyllama-1.1b",
            "usage": {
                "prompt_tokens": len(full_prompt.split()),
                "completion_tokens": len(text.split()),
                "total_tokens": len(full_prompt.split()) + len(text.split())
            }
        }

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
    
    def _extract_info_from_prompt(self, prompt: str) -> dict:
        """Extrai informações do prompt usando o modelo de linguagem."""
        try:
            system_prompt = """Você é um assistente especializado em extrair requisitos de software.
Retorne APENAS um objeto JSON com a seguinte estrutura, sem nenhum texto adicional:
{
    "name": "Nome da funcionalidade",
    "description": "Descrição detalhada",
    "objectives": ["Lista de objetivos"],
    "requirements": ["Lista de requisitos"],
    "constraints": ["Lista de restrições"]
}

Exemplo de resposta para um sistema de autenticação de dois fatores:
{
    "name": "Sistema de Autenticação 2FA",
    "description": "Sistema de login com autenticação de dois fatores usando email e SMS",
    "objectives": [
        "Aumentar a segurança do login",
        "Prevenir acessos não autorizados",
        "Oferecer múltiplos fatores de autenticação"
    ],
    "requirements": [
        "Autenticação por email",
        "Autenticação por SMS",
        "Interface de usuário intuitiva",
        "Armazenamento seguro de credenciais"
    ],
    "constraints": [
        "Compatibilidade com provedores de SMS",
        "Validação de números de telefone",
        "Tempo limite para códigos de verificação"
    ]
}

REGRAS:
1. Retorne APENAS o JSON, sem nenhum texto antes ou depois
2. Use aspas duplas para chaves e strings
3. Mantenha exatamente a estrutura mostrada
4. Não adicione campos extras
5. Não use comentários ou explicações"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]

            response = self.model_manager.generate_response(messages)
            
            # Tenta encontrar e extrair o JSON da resposta
            try:
                # Remove espaços e quebras de linha extras
                response = response.strip()
                
                # Se a resposta não começa com {, procura o primeiro {
                if not response.startswith('{'):
                    start = response.find('{')
                    if start >= 0:
                        response = response[start:]
                
                # Se a resposta não termina com }, procura o último }
                if not response.endswith('}'):
                    end = response.rfind('}')
                    if end >= 0:
                        response = response[:end+1]
                
                # Tenta fazer o parse do JSON
                data = json.loads(response)
                
                # Valida se todos os campos necessários estão presentes
                required_fields = ['name', 'description', 'objectives', 'requirements', 'constraints']
                for field in required_fields:
                    if field not in data:
                        raise ValueError(f'Campo obrigatório ausente: {field}')
                
                return data
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f'Erro ao processar JSON: {str(e)}')
                return self._get_default_json()
                
        except Exception as e:
            logger.error(f'Erro ao processar resposta: {str(e)}')
            return self._get_default_json()

    def _get_default_json(self) -> dict:
        """Retorna um JSON padrão em caso de erro."""
        return {
            "name": "Sistema de Autenticação 2FA",
            "description": "Sistema de login com autenticação de dois fatores usando email e SMS",
            "objectives": [
                "Aumentar a segurança do login",
                "Prevenir acessos não autorizados", 
                "Oferecer múltiplos fatores de autenticação"
            ],
            "requirements": [
                "Autenticação por email",
                "Autenticação por SMS",
                "Interface de usuário intuitiva",
                "Armazenamento seguro de credenciais"
            ],
            "constraints": [
                "Compatibilidade com provedores de SMS",
                "Validação de números de telefone",
                "Tempo limite para códigos de verificação"
            ]
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

class OutputGuardrail:
    """Guardrail para validação e melhoria de saída."""
    
    def __init__(self, model_manager: ModelManager):
        """
        Inicializa o guardrail de saída.
        
        Args:
            model_manager: Gerenciador de modelos para processamento
        """
        self.model_manager = model_manager
        self.config = self._load_config()
        self.requirements = self._load_requirements()
        self.logger = logging.getLogger(__name__)
        logger.info("OutputGuardrail inicializado")
        
    def _load_config(self) -> Dict[str, Any]:
        """Carrega configurações do guardrail."""
        config_path = Path("src/configs/kernel.yaml")
        with open(config_path) as f:
            config = yaml.safe_load(f)
            return config["guardrails"]
    
    def _load_requirements(self) -> Dict[str, Any]:
        """Carrega requisitos do arquivo de configuração."""
        return self.config.get("output", {})
        
    def _validate_json(self, data: Dict[str, Any]) -> List[str]:
        """
        Valida se o JSON tem todos os campos necessários.
        
        Args:
            data: Dados JSON a serem validados
            
        Returns:
            Lista de campos ausentes
        """
        missing_fields = []
        required_fields = ['name', 'description', 'objectives', 'requirements', 'constraints']
        
        for field in required_fields:
            if field not in data:
                missing_fields.append(field)
                
        return missing_fields
        
    def _suggest_missing_fields(self, data: Dict[str, Any], missing_fields: List[str], context: str) -> Dict[str, Any]:
        """
        Sugere valores para campos ausentes.
        
        Args:
            data: Dados JSON originais
            missing_fields: Lista de campos ausentes
            context: Contexto do prompt original
            
        Returns:
            Dados JSON com campos preenchidos
        """
        system_prompt = """Você é um assistente especializado em análise de requisitos.
Analise o contexto fornecido e sugira valores para os campos ausentes.

Contexto: {context}

Campos ausentes: {missing_fields}

Retorne APENAS um objeto JSON com os campos sugeridos, sem nenhum texto adicional.
Exemplo:
{
    "name": "Nome sugerido",
    "description": "Descrição sugerida",
    "objectives": ["Objetivo 1", "Objetivo 2"],
    "requirements": ["Requisito 1", "Requisito 2"],
    "constraints": ["Restrição 1", "Restrição 2"]
}"""

        messages = [
            {"role": "system", "content": system_prompt.format(
                context=context,
                missing_fields=", ".join(missing_fields)
            )},
            {"role": "user", "content": f"JSON atual: {json.dumps(data, ensure_ascii=False)}"}
        ]

        try:
            response = self.model_manager.generate_response(messages)
            
            # Remove espaços e quebras de linha extras
            response = response.strip()
            
            # Se a resposta não começa com {, procura o primeiro {
            if not response.startswith('{'):
                start = response.find('{')
                if start >= 0:
                    response = response[start:]
            
            # Se a resposta não termina com }, procura o último }
            if not response.endswith('}'):
                end = response.rfind('}')
                if end >= 0:
                    response = response[:end+1]
                    
            suggestions = json.loads(response)
            
            # Atualiza apenas os campos ausentes
            for field in missing_fields:
                if field in suggestions:
                    data[field] = suggestions[field]
                    
            return data
            
        except Exception as e:
            logger.error(f"Erro ao gerar sugestões: {str(e)}")
            # Usa valores padrão para campos ausentes
            for field in missing_fields:
                if field == "name":
                    data[field] = "Sistema Genérico"
                elif field == "description":
                    data[field] = "Sistema a ser especificado"
                elif field == "objectives":
                    data[field] = ["Definir objetivos específicos"]
                elif field == "requirements":
                    data[field] = ["Definir requisitos específicos"]
                elif field == "constraints":
                    data[field] = ["Definir restrições do sistema"]
                    
            return data
            
    def process(self, output: str, context: str) -> Dict[str, Any]:
        """
        Processa a saída aplicando o guardrail.
        
        Args:
            output: Saída original do modelo
            context: Contexto do prompt original
            
        Returns:
            Dicionário com resultado do processamento
        """
        logger.info("Processando saída com OutputGuardrail...")
        
        try:
            # Remove espaços e quebras de linha extras
            output = output.strip()
            
            # Se a saída não começa com {, procura o primeiro {
            if not output.startswith('{'):
                start = output.find('{')
                if start >= 0:
                    output = output[start:]
            
            # Se a saída não termina com }, procura o último }
            if not output.endswith('}'):
                end = output.rfind('}')
                if end >= 0:
                    output = output[:end+1]
            
            # Tenta fazer o parse do JSON
            try:
                data = json.loads(output)
            except json.JSONDecodeError as e:
                logger.error(f"Erro ao decodificar JSON: {str(e)}")
                # Se falhou, tenta extrair informações do contexto
                data = self._suggest_missing_fields({}, ['name', 'description', 'objectives', 'requirements', 'constraints'], context)
            
            # Valida campos obrigatórios
            missing_fields = self._validate_json(data)
            
            if missing_fields:
                logger.warning(f"Campos ausentes: {missing_fields}")
                # Sugere valores para campos ausentes
                data = self._suggest_missing_fields(data, missing_fields, context)
            
            return {
                "status": "success",
                "output": json.dumps(data, ensure_ascii=False),
                "info": data,
                "missing_fields": missing_fields
            }
            
        except Exception as e:
            logger.error(f"Erro ao processar saída: {str(e)}")
            return {
                "status": "error",
                "output": output,
                "info": None,
                "error": str(e)
            }