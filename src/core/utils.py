"""
Utilitários para o sistema.
Módulo com funções comuns usadas em diferentes partes do sistema.
"""
import os

from typing import Optional, Any, List
import json
from datetime import datetime

def mask_sensitive_data(data: Any, mask_str: str = '***') -> Any:
    """
    Mascara dados sensíveis em strings e dicionários.
    
    Args:
        data: Dados a serem mascarados (string, dict ou outro tipo)
        mask_str: String de substituição para dados sensíveis
        
    Returns:
        Dados com informações sensíveis mascaradas
    """
    # Se for None, retorna diretamente
    if data is None:
        return None
        
    # Se for uma string, verificar e mascarar dados sensíveis
    if isinstance(data, str):
        return mask_partially(data, mask_str)
        
    # Se for um dicionário, processar valores recursivamente
    elif isinstance(data, dict):
        masked_data = {}
        for key, value in data.items():
            # Chaves sensíveis são completamente mascaradas
            if any(keyword in key.lower() for keyword in [
                'password', 'senha', 'secret', 'token', 'key', 'auth', 'credential', 'private'
            ]):
                masked_data[key] = mask_str
            else:
                # Processar valores normais recursivamente
                masked_data[key] = mask_sensitive_data(value, mask_str)
        return masked_data
        
    # Se for uma lista, processar itens
    elif isinstance(data, list):
        return [mask_sensitive_data(item, mask_str) for item in data]
        
    # Para outros tipos, retornar sem alteração
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

def get_env_status(var_name: str) -> str:
    """
    Retorna o status de uma variável de ambiente sem expor seu valor.
    
    Args:
        var_name: Nome da variável de ambiente
        
    Returns:
        String indicando o status da variável
    """
    # Lista de palavras-chave para identificar dados sensíveis
    SENSITIVE_KEYWORDS = [
        'pass', 'senha', 'password', 
        'token', 'access_token', 'refresh_token', 'jwt', 
        'secret', 'api_key', 'apikey', 'key', 
        'auth', 'credential', 'oauth', 
        'private', 'signature'
    ]
    
    value = os.environ.get(var_name)
    if not value:
        return "não definido"
    elif any(keyword in var_name.lower() for keyword in SENSITIVE_KEYWORDS):
        return "configurado"
    else:
        # Para variáveis não sensíveis, podemos retornar o valor
        # Mas aplicamos mascaramento para garantir segurança
        return mask_partially(value)

def log_env_status(logger, env_vars: List[str]) -> None:
    """
    Loga o status de múltiplas variáveis de ambiente.
    
    Args:
        logger: Instância do logger
        env_vars: Lista de nomes de variáveis de ambiente
    """
    for var in env_vars:
        status = get_env_status(var)
        logger.info(f"Variável de ambiente {var}: {status}")

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
