# src/core/logger.py
import os
import logging
import logging.handlers
import uuid
import time
import re
from contextvars import ContextVar
from pathlib import Path
from functools import wraps
from typing import Optional, Dict, Any, List, Tuple, Callable
from dataclasses import dataclass, field
import json
from datetime import datetime
import functools
import yaml

# Diretório base do projeto
BASE_DIR = Path(__file__).resolve().parent.parent.parent

def load_config() -> Dict[str, Any]:
    """
    Carrega as configurações do logger do arquivo YAML.
    
    Returns:
        Dict com as configurações
    """
    config_path = os.path.join(BASE_DIR, 'src', 'configs', 'logger.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

# Carrega configurações
CONFIG = load_config()

# Configura diretório de logs
LOG_DIR = os.path.join(BASE_DIR, CONFIG['directories']['logs'])
os.makedirs(LOG_DIR, exist_ok=True)

# Configuração de níveis de log
LOG_LEVEL_MAP = CONFIG['log_levels']['map']
DEFAULT_LOG_LEVEL = CONFIG['log_levels']['default']
LOG_LEVEL = os.environ.get('LOG_LEVEL', DEFAULT_LOG_LEVEL).upper()
NUMERIC_LOG_LEVEL = LOG_LEVEL_MAP.get(LOG_LEVEL, LOG_LEVEL_MAP['INFO'])

# Lista de palavras-chave para identificar dados sensíveis
SENSITIVE_KEYWORDS = CONFIG['security']['sensitive_keywords']

# Padrões de tokens a serem mascarados
TOKEN_PATTERNS = CONFIG['security']['token_patterns']

class SecureLogFilter(logging.Filter):
    """Filtro para mascarar dados sensíveis nos registros de log"""
    
    def __init__(self):
        super().__init__()
        self.mask_config = CONFIG['security']['masking']
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Processa e mascara dados sensíveis no registro de log"""
        record.msg = self.mask_sensitive_data(record.msg)
        if isinstance(record.args, dict):
            record.args = self.mask_sensitive_data(record.args)
        else:
            record.args = tuple(self.mask_sensitive_data(arg) for arg in record.args)
        return True

    def mask_sensitive_data(self, data: Any, mask_str: Optional[str] = None) -> Any:
        """Mascara dados sensíveis em strings e estruturas de dados"""
        mask_str = mask_str or self.mask_config['default_mask']
        if isinstance(data, dict):
            return {k: self.mask_value(k, v, mask_str) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.mask_sensitive_data(item, mask_str) for item in data]
        elif isinstance(data, str):
            return self.mask_string(data, mask_str)
        return data

    def mask_value(self, key: str, value: Any, mask_str: str) -> Any:
        """Mascara valores sensíveis baseado na chave e conteúdo"""
        if any(keyword in key.lower() for keyword in SENSITIVE_KEYWORDS):
            return mask_str
        return self.mask_sensitive_data(value, mask_str)

    def mask_string(self, text: str, mask_str: str) -> str:
        """Mascara padrões sensíveis em strings"""
        if len(text) > self.mask_config['min_length_for_masking']:
            for pattern in TOKEN_PATTERNS:
                if re.search(pattern, text):
                    return self.mask_partially(text, mask_str)
        if any(keyword in text.lower() for keyword in SENSITIVE_KEYWORDS):
            return self.mask_partially(text, mask_str)
        return text

    def mask_partially(self, text: str, mask_str: str) -> str:
        """Mascara parcialmente mantendo parte do conteúdo"""
        if len(text) <= self.mask_config['min_length_for_partial']:
            return mask_str
        prefix = text[:self.mask_config['prefix_length']]
        suffix = text[-self.mask_config['suffix_length']:] if len(text) > (self.mask_config['prefix_length'] + self.mask_config['suffix_length']) else ''
        return f"{prefix}{mask_str}{suffix}"

def setup_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Configura um logger com o formato padrão.
    
    Args:
        name: Nome do logger
        level: Nível de log (DEBUG, INFO, etc)
        
    Returns:
        Logger configurado
    """
    # Cria logger
    logger = logging.getLogger(name)
    
    # Define nível
    log_level = level or os.getenv("LOG_LEVEL", CONFIG['log_levels']['default'])
    logger.setLevel(getattr(logging, log_level))
    
    # Remove handlers existentes
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Adiciona handler de console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    
    # Define formato
    formatter = logging.Formatter(CONFIG['format']['default'])
    console_handler.setFormatter(formatter)
    
    # Adiciona filtro de segurança
    secure_filter = SecureLogFilter()
    console_handler.addFilter(secure_filter)
    
    # Adiciona handler
    logger.addHandler(console_handler)
    
    return logger

def log_execution(func: Callable) -> Callable:
    """
    Decorador para logging de execução de funções.
    
    Args:
        func: Função a ser decorada
        
    Returns:
        Função decorada com logging
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        
        # Log de início
        logger.info(f"INÍCIO - {func.__name__} | Args: {args}, Kwargs: {kwargs}")
        
        try:
            # Executa função
            result = func(*args, **kwargs)
            
            # Log de sucesso
            logger.info(f"SUCESSO - {func.__name__}")
            return result
            
        except Exception as e:
            # Log de erro
            logger.error(
                f"FALHA - {func.__name__} | Erro: {str(e)}", 
                exc_info=True
            )
            raise
            
    return wrapper

def log_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
    """
    Loga um erro com contexto adicional.
    
    Args:
        error: Exceção a ser logada
        context: Dicionário com informações de contexto
    """
    logger = get_logger(__name__)
    
    error_data = {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'timestamp': datetime.now().isoformat(),
        'context': context or {}
    }
    
    logger.error(
        f"Erro: {json.dumps(error_data, indent=2)}", 
        exc_info=True
    )

# Alias para compatibilidade
get_logger = setup_logger

# Logger global padrão
logger = setup_logger('agent_flow_tdd')

# Funções auxiliares de conveniência
def log_error(message: str, exc_info=False) -> None:
    """Registra erro com stacktrace opcional"""
    logger.error(message, exc_info=exc_info)

def log_warning(message: str) -> None:
    """Registra aviso"""
    logger.warning(message)

def log_info(message: str) -> None:
    """Registra informação"""
    logger.info(message)

def log_debug(message: str) -> None:
    """Registra mensagem de debug"""
    logger.debug(message)

def get_child_logger(name: str) -> logging.Logger:
    """Obtém um logger filho configurado"""
    return logger.getChild(name)

# Context variables para tracing
current_trace: ContextVar[Optional['Trace']] = ContextVar('current_trace', default=None)
current_span: ContextVar[Optional['Span']] = ContextVar('current_span', default=None)

@dataclass
class Span:
    """Representa uma operação temporal dentro de um trace"""
    trace_id: str
    span_id: str = field(default_factory=lambda: f"{CONFIG['trace']['prefixes']['span']}{uuid.uuid4().hex}")
    parent_id: Optional[str] = None
    span_type: str = CONFIG['trace']['default_span_type']
    name: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    span_data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

@dataclass
class Trace:
    """Representa um fluxo completo de execução"""
    trace_id: str = field(default_factory=lambda: f"{CONFIG['trace']['prefixes']['trace']}{uuid.uuid4().hex}")
    workflow_name: str = CONFIG['trace']['default_workflow_name']
    group_id: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    spans: List[Span] = field(default_factory=list)
    disabled: bool = False
    config: 'TraceConfig' = field(default_factory=lambda: TraceConfig())

@dataclass
class TraceConfig:
    """Configuração para controle do tracing"""
    tracing_disabled: bool = CONFIG['trace']['tracing_disabled']
    trace_include_sensitive_data: bool = CONFIG['trace']['trace_include_sensitive_data']
    trace_processors: List['TraceProcessor'] = field(default_factory=list)

class TraceProcessor:
    """Interface para processamento de traces"""
    def process_trace(self, trace: Trace):
        raise NotImplementedError

class FileTraceProcessor(TraceProcessor):
    """Processador que salva traces em arquivo"""
    
    def __init__(self, file_path: Optional[str] = None):
        self.file_path = file_path or CONFIG['trace']['file_processor']['default_file']

def trace(
    workflow_name: str = CONFIG['trace']['default_workflow_name'],
    group_id: Optional[str] = None,
    disabled: Optional[bool] = None,
    metadata: Optional[Dict] = None
):
    """Context manager para criação de traces"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger('agent_flow_tdd')
            if logger.trace_config.tracing_disabled or disabled:
                return func(*args, **kwargs)

            current_trace.get()
            new_trace = Trace(
                workflow_name=workflow_name,
                group_id=group_id,
                metadata=metadata or {},
                config=logger.trace_config
            )

            token = current_trace.set(new_trace)
            try:
                result = func(*args, **kwargs)
                new_trace.end_time = time.time()
                
                # Processar trace
                for processor in logger.trace_config.trace_processors:
                    processor.process_trace(new_trace)
                
                return result
            except Exception as e:
                new_trace.end_time = time.time()
                new_trace.metadata['error'] = str(e)
                raise
            finally:
                current_trace.reset(token)

        return wrapper
    return decorator

def span(
    span_type: str = CONFIG['trace']['default_span_type'],
    name: Optional[str] = None,
    capture_args: bool = False
):
    """Decorador para criação de spans"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_t = current_trace.get()
            current_s = current_span.get()
            
            if not current_t or current_t.disabled:
                return func(*args, **kwargs)

            new_span = Span(
                trace_id=current_t.trace_id,
                parent_id=current_s.span_id if current_s else None,
                span_type=span_type,
                name=name or func.__name__,
                span_data={
                    'function': func.__name__,
                    'module': func.__module__,
                    'args': mask_arguments(args, kwargs) if capture_args else None
                }
            )

            token = current_span.set(new_span)
            try:
                result = func(*args, **kwargs)
                new_span.end_time = time.time()
                current_t.spans.append(new_span)
                return result
            except Exception as e:
                new_span.end_time = time.time()
                new_span.error = str(e)
                current_t.spans.append(new_span)
                raise
            finally:
                current_span.reset(token)

        return wrapper
    return decorator

def mask_arguments(args: Tuple, kwargs: Dict) -> Dict:
    """Mascara argumentos sensíveis para inclusão nos spans"""
    masked_args = [SecureLogFilter().mask_sensitive_data(arg) for arg in args]
    masked_kwargs = {
        k: SecureLogFilter().mask_sensitive_data(v) if 'password' not in k else '***'
        for k, v in kwargs.items()
    }
    return {'args': masked_args, 'kwargs': masked_kwargs}

# Span types específicos
def agent_span(name: str = "Agent Run"):
    return span(span_type="agent", name=name, capture_args=True)

def generation_span(name: str = "LLM Generation"):
    return span(span_type="generation", name=name)

def tool_span(name: str = "Tool Execution"):
    return span(span_type="tool", name=name, capture_args=True)
