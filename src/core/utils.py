"""
Utilitários para o sistema.
Módulo com funções comuns usadas em diferentes partes do sistema.
"""
import os
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, List, Dict, Tuple, Union

from src.core.logger import get_logger, log_execution

logger = get_logger(__name__)

@log_execution
def setup_paths():
    """Configura e valida os caminhos base do projeto"""
    logger.info("INÍCIO - setup_paths | Configurando caminhos base")
    
    try:
        # Constrói caminhos dentro do projeto
        base_dir = Path(__file__).resolve().parent.parent.parent
        logger.debug(f"Diretório base: {base_dir}")

        # Configurações de caminhos
        log_dir = os.path.join(base_dir, 'run', 'logs')
        configs_dir = os.path.join(base_dir, 'configs')

        # Criar diretórios se não existirem
        os.makedirs(log_dir, exist_ok=True)
        os.makedirs(configs_dir, exist_ok=True)
        
        logger.info("SUCESSO - Caminhos configurados e validados")
        return base_dir, log_dir, configs_dir
        
    except Exception as e:
        logger.error(f"FALHA - setup_paths | Erro: {str(e)}", exc_info=True)
        raise

# Executa a configuração de caminhos
BASE_DIR, LOG_DIR, CONFIGS_DIR = setup_paths()

def get_env_var(name: str, default: Optional[str] = None, args_value: Optional[str] = None) -> Optional[str]:
    """
    Obtém uma variável de ambiente, priorizando args sobre os.environ.

    Args:
        name: Nome da variável.
        default: Valor padrão se a variável não existir.
        args_value: Valor passado via argumentos de linha de comando.

    Returns:
        Valor da variável ou None se não encontrada.
    """
    # Prioriza valor passado via args
    if args_value is not None:
        return args_value
    
    # Se não houver valor em args, tenta os.environ
    return os.environ.get(name, default)


def get_env_status() -> Dict[str, Dict[str, bool]]:
    """
    Verifica o status das variáveis de ambiente necessárias.

    Returns:
        Dicionário com o status de cada variável.
    """
    required_vars = {
        "OPENAI_KEY": False,
        "GITHUB_TOKEN": False,
        "GITHUB_OWNER": False,
        "GITHUB_REPO": False,
    }

    optional_vars = {
        "OPENROUTER_KEY": False,
        "DEEPSEEK_KEY": False,
        "GEMINI_KEY": False,
        "DEFAULT_MODEL": False,
        "ELEVATION_MODEL": False,
        "FALLBACK_ENABLED": False,
        "MODEL_TIMEOUT": False,
        "MAX_RETRIES": False,
        "CACHE_ENABLED": False,
        "CACHE_TTL": False,
        "CACHE_DIR": False,
        "LOG_LEVEL": False,
        "LOG_FILE": False,
    }

    # Verifica variáveis obrigatórias
    for var in required_vars:
        required_vars[var] = bool(get_env_var(var))

    # Verifica variáveis opcionais
    for var in optional_vars:
        optional_vars[var] = bool(get_env_var(var))

    return {
        "required": required_vars,
        "optional": optional_vars,
        "all_required_set": all(required_vars.values()),
    }


def validate_env() -> None:
    """
    Valida se todas as variáveis de ambiente obrigatórias estão definidas.

    Raises:
        ValueError: Se alguma variável obrigatória não estiver definida.
    """
    status = get_env_status()
    if not status["all_required_set"]:
        missing = [var for var, set_ in status["required"].items() if not set_]
        raise ValueError(
            f"Variáveis de ambiente obrigatórias não definidas: {', '.join(missing)}\n"
            "IMPORTANTE: Não use arquivos .env. Configure as variáveis diretamente no ambiente ou via argumentos."
        )

def mask_sensitive_data(data: Union[str, Dict[str, Any], List[Any]]) -> Union[str, Dict[str, Any], List[Any]]:
    """
    Mascara dados sensíveis em strings, dicionários ou listas.

    Args:
        data: Dados a serem mascarados. Pode ser uma string, dicionário ou lista.

    Returns:
        Dados com informações sensíveis mascaradas.
    """
    if isinstance(data, str):
        # Mascara tokens e chaves de API
        patterns = [
            (r'["\']?[a-zA-Z0-9-_]{20,}["\']?', '***API_KEY***'),  # API keys
            (r'Bearer\s+[a-zA-Z0-9-_.]+', 'Bearer ***TOKEN***'),  # Bearer tokens
            (r'github_pat_[a-zA-Z0-9_]+', '***GITHUB_PAT***'),  # GitHub PATs
            (r'ghp_[a-zA-Z0-9]+', '***GITHUB_TOKEN***'),  # GitHub tokens
            (r'sk-[a-zA-Z0-9]+', '***OPENAI_KEY***'),  # OpenAI keys
        ]
        masked = data
        for pattern, replacement in patterns:
            masked = re.sub(pattern, replacement, masked)
        return masked
    elif isinstance(data, dict):
        return {k: mask_sensitive_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [mask_sensitive_data(item) for item in data]
    return data

def mask_partially(text, mask_str='***'):
    """
    Mascara parcialmente conteúdo sensível, mantendo caracteres iniciais.
    
    Args:
        text: Texto a ser mascarado
        mask_str: String de substituição
        
    Returns:
        Texto mascarado
    """
    if not text or len(text) < 8:
        return mask_str
        
    # Mostra os primeiros 4 caracteres e mascara o resto
    visible = min(4, len(text) // 3)
    return text[:visible] + mask_str

def format_timestamp(timestamp: str) -> str:
    """
    Formata timestamp para exibição.
    
    Args:
        timestamp: String com o timestamp
        
    Returns:
        String formatada no padrão YYYY-MM-DD HH:MM:SS
    """
    try:
        dt = datetime.fromisoformat(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return timestamp

def format_json(data: str) -> str:
    """
    Formata JSON para exibição.
    
    Args:
        data: String com o JSON
        
    Returns:
        String formatada com indentação
    """
    try:
        parsed = json.loads(data)
        return json.dumps(parsed, indent=2)
    except:
        return data

"""
Utilitário para validação de tokens e chaves de API.
"""

class TokenValidator:
    """
    Validador de tokens de API e chaves de ambiente.
    Garante que os tokens necessários estejam presentes e válidos.
    """
    
    @staticmethod
    def validate_token(token: Optional[str], token_name: str, required: bool = True) -> bool:
        """
        Valida se um token está presente e tem uma estrutura mínima válida.
        
        Args:
            token: O token a ser validado
            token_name: Nome do token para mensagens de erro
            required: Se o token é obrigatório
            
        Returns:
            bool: True se o token for válido, False caso contrário
            
        Raises:
            ValueError: Se o token for obrigatório e estiver ausente ou inválido
        """
        if not token or token.strip() == "":
            if required:
                raise ValueError(f"Token {token_name} é obrigatório mas não foi encontrado nas variáveis de ambiente")
            return False
            
        # Verificação básica de estrutura mínima (pelo menos 10 caracteres, sem espaços)
        if len(token) < 10 or " " in token:
            if required:
                raise ValueError(f"Token {token_name} parece inválido (formato incorreto)")
            return False
            
        return True
    
    @staticmethod
    def validate_openai_token(token: Optional[str] = None, required: bool = True) -> bool:
        """
        Valida token da OpenAI, com verificações específicas para o formato do token.
        
        Args:
            token: Token da OpenAI. Se None, será buscado na variável de ambiente
            required: Se o token é obrigatório
            
        Returns:
            bool: True se o token for válido, False caso contrário
            
        Raises:
            ValueError: Se o token for obrigatório e estiver ausente ou inválido
        """
        # Se não fornecido, tenta buscar da variável de ambiente
        if token is None:
            token = os.environ.get("OPENAI_KEY", "")
            
        # Verificação específica para tokens da OpenAI (geralmente começam com "sk-")
        if token and not token.startswith("sk-"):
            if required:
                raise ValueError("Token da OpenAI inválido (deve começar com 'sk-')")
            return False
            
        return TokenValidator.validate_token(token, "OpenAI", required)
        
    @staticmethod
    def validate_github_token(token: Optional[str] = None, required: bool = True) -> bool:
        """
        Valida token do GitHub, com verificações específicas para o formato do token.
        
        Args:
            token: Token do GitHub. Se None, será buscado na variável de ambiente
            required: Se o token é obrigatório
            
        Returns:
            bool: True se o token for válido, False caso contrário
            
        Raises:
            ValueError: Se o token for obrigatório e estiver ausente ou inválido
        """
        # Se não fornecido, tenta buscar da variável de ambiente
        if token is None:
            token = os.environ.get("GITHUB_TOKEN", "")
            
        # GitHub tokens geralmente têm um formato específico, como começar com "ghp_"
        # Mas isso pode variar, então faremos uma verificação básica
        
        return TokenValidator.validate_token(token, "GitHub", required)
    
    @staticmethod
    def validate_all_required_tokens() -> bool:
        """
        Valida todos os tokens obrigatórios para o sistema.
        
        Returns:
            bool: True se todos os tokens obrigatórios estiverem válidos
            
        Raises:
            ValueError: Detalhando quais tokens estão faltando ou são inválidos
        """
        missing_tokens = []
        
        try:
            TokenValidator.validate_openai_token(required=True)
        except ValueError as e:
            missing_tokens.append(str(e))
            
        try:
            TokenValidator.validate_github_token(required=True)
        except ValueError as e:
            missing_tokens.append(str(e))
            
        if missing_tokens:
            raise ValueError(f"Tokens obrigatórios faltando ou inválidos: {', '.join(missing_tokens)}")
            
        return True 


COMMIT_TYPES = {
    'feat': 'minor',  # Novas funcionalidades
    'fix': 'patch',   # Correções de bugs
    'docs': 'patch',  # Documentação
    'style': 'patch', # Formatação
    'refactor': 'patch', # Refatoração
    'test': 'patch',  # Testes
    'chore': 'patch', # Manutenção
    'perf': 'patch',  # Performance
    'ci': 'patch',    # CI/CD
    'build': 'patch', # Build
    'breaking': 'major' # Breaking changes
}

BREAKING_PATTERNS = [
    r'breaking change',
    r'breaking-change',
    r'incompatible',
    r'não compatível',
    r'breaking',
    r'major update'
]

FEATURE_PATTERNS = [
    r'add(?:ed|ing)?\s+(?:new\s+)?(?:feature|functionality)',
    r'implement(?:ed|ing)?',
    r'criado?\s+(?:novo|nova)',
    r'adiciona(?:do|ndo)?',
    r'nova\s+funcionalidade',
    r'novo\s+recurso'
]

FIX_PATTERNS = [
    r'fix(?:ed|ing)?',
    r'bug\s*fix',
    r'resolve[sd]?',
    r'corrig(?:e|ido|indo)',
    r'conserta(?:do|ndo)?',
    r'correc[aã]o'
]

class VersionAnalyzer:
    """
    Analisador de versões para controle semântico.
    """

    def __init__(self):
        self.logger = get_logger(__name__)

    @log_execution
    def analyze_commit_message(self, message: str) -> str:
        """
        Analisa a mensagem do commit para determinar o tipo de versão a ser incrementada.
        
        Args:
            message: Mensagem do commit
            
        Returns:
            str: Tipo de versão ('major', 'minor' ou 'patch')
        """
        message = message.lower()
        
        # Verifica breaking changes
        for pattern in BREAKING_PATTERNS:
            if re.search(pattern, message, re.IGNORECASE):
                return 'major'
        
        # Verifica novas funcionalidades
        for pattern in FEATURE_PATTERNS:
            if re.search(pattern, message, re.IGNORECASE):
                return 'minor'
        
        # Verifica correções
        for pattern in FIX_PATTERNS:
            if re.search(pattern, message, re.IGNORECASE):
                return 'patch'
        
        # Se não identificou nenhum padrão específico, assume patch
        return 'patch'

    @log_execution
    def get_current_version(self) -> Tuple[str, Dict]:
        """
        Obtém a versão atual do projeto.
        
        Returns:
            Tuple[str, Dict]: Versão atual e dados do version_commits.json
        """
        try:
            with open('version_commits.json', 'r') as f:
                data = json.load(f)
                versions = sorted(data.keys())
                if versions:
                    return versions[-1], data
        except Exception as e:
            self.logger.error(f"Erro ao ler version_commits.json: {str(e)}")
        
        return "0.1.0", {}

    @log_execution
    def get_last_commit_info(self) -> Optional[Tuple[str, str]]:
        """
        Obtém informações do último commit.
        
        Returns:
        Optional[Tuple[str, str]]: (hash do commit, mensagem do commit) ou None se falhar
        """
        try:
            commit_hash = os.popen('git rev-parse --short HEAD').read().strip()
            commit_msg = os.popen('git log -1 --pretty=%B').read().strip()
            return commit_hash, commit_msg
        except Exception as e:
            self.logger.error(f"Erro ao obter informações do último commit: {str(e)}")
            return None

    @log_execution
    def increment_version(self, current: str, increment_type: str) -> str:
        """
        Incrementa a versão baseado no tipo de incremento.
        
        Args:
            current: Versão atual
            increment_type: Tipo de incremento ('major', 'minor' ou 'patch')
            
        Returns:
            str: Nova versão
        """
        try:
            # Se a versão atual usa o formato de data
            if re.match(r'\d{4}\.\d{2}\.\d{2}', current):
                import time
                return f"{time.strftime('%Y.%m.%d')}.1"
            
            # Versão semântica padrão
            parts = current.split('.')
            if len(parts) < 3:
                parts.extend(['0'] * (3 - len(parts)))
            
            major, minor, patch = map(lambda x: int(re.search(r'\d+', x).group()), parts[:3])
            
            if increment_type == 'major':
                return f"{major + 1}.0.0"
            elif increment_type == 'minor':
                return f"{major}.{minor + 1}.0"
            else:  # patch
                return f"{major}.{minor}.{patch + 1}"
        except Exception as e:
            self.logger.error(f"Erro ao incrementar versão: {str(e)}")
            return current

    @log_execution
    def update_version_files(self, new_version: str) -> bool:
        """
        Atualiza os arquivos que contêm a versão.
        
        Args:
            new_version: Nova versão a ser definida
            
        Returns:
            bool: True se a atualização foi bem sucedida
        """
        try:
            # Atualiza setup.py
            with open('setup.py', 'r') as f:
                content = f.read()
            content = re.sub(r'version="[^"]*"', f'version="{new_version}"', content)
            with open('setup.py', 'w') as f:
                f.write(content)
                
            # Atualiza __init__.py
            with open('src/__init__.py', 'r') as f:
                content = f.read()
            content = re.sub(r'__version__\s*=\s*"[^"]*"', f'__version__ = "{new_version}"', content)
            with open('src/__init__.py', 'w') as f:
                f.write(content)
                
            return True
        except Exception as e:
            self.logger.error(f"Erro ao atualizar arquivos de versão: {str(e)}")
            return False

    @log_execution
    def smart_bump(self) -> Optional[str]:
        """
        Realiza o bump de versão de forma inteligente, analisando o último commit.
        
        Returns:
            Optional[str]: Nova versão ou None se falhar
        """
        # Obtém informações do último commit
        commit_info = self.get_last_commit_info()
        if not commit_info:
            return None
        
        commit_hash, commit_msg = commit_info
        
        # Analisa a mensagem do commit
        increment_type = self.analyze_commit_message(commit_msg)
        
        # Obtém versão atual
        current_version, version_data = self.get_current_version()
        
        # Incrementa a versão
        new_version = self.increment_version(current_version, increment_type)
        
        # Atualiza os arquivos
        if not self.update_version_files(new_version):
            return None
        
        # Atualiza version_commits.json
        version_data[new_version] = {
            'commit_hash': commit_hash,
            'timestamp': os.popen('date "+%Y-%m-%d %H:%M:%S"').read().strip(),
            'increment_type': increment_type,
            'previous_version': current_version
        }
        
        try:
            with open('version_commits.json', 'w') as f:
                json.dump(version_data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Erro ao atualizar version_commits.json: {str(e)}")
            return None
        
        return new_version