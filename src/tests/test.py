"""
Testes unificados para o projeto.
Inclui testes de CLI, banco de dados e download de modelos.
"""

import json
import os
from unittest.mock import patch, Mock, MagicMock
import yaml
from pathlib import Path

import pytest

from src.cli import app
from src.core.agents import AgentOrchestrator, AgentResult, InputGuardrail, OutputGuardrail
from src.core.db import DatabaseManager
from src.core.models import ModelManager
from src.core.logger import get_logger

logger = get_logger(__name__)

# Carrega configurações de teste
def load_test_config() -> dict:
    """Carrega configurações de teste do arquivo YAML."""
    config_path = Path(__file__).resolve().parent.parent / 'configs' / 'test.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

TEST_CONFIG = load_test_config()

# Conteúdo do Makefile para testes de download
MAKEFILE_CONTENT = '''
.PHONY: download-model install

MODEL_URL = https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
MODEL_NAME = tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
MODEL_DIR = models

# Download do modelo TinyLLaMA
download-model:
	@echo "📥 Baixando modelo TinyLLaMA..."
	@mkdir -p $(MODEL_DIR)
	@if [ -f "$(MODEL_DIR)/$(MODEL_NAME)" ]; then \
		echo "✅ Modelo já existe em $(MODEL_DIR)/$(MODEL_NAME)"; \
	else \
		echo "🔄 Iniciando download..."; \
		if ! curl -L -f $(MODEL_URL) -o $(MODEL_DIR)/$(MODEL_NAME); then \
			echo "❌ Falha no download do modelo"; \
			rm -f $(MODEL_DIR)/$(MODEL_NAME); \
			exit 1; \
		fi; \
		echo "✅ Download concluído em $(MODEL_DIR)/$(MODEL_NAME)"; \
	fi

# Instalação e setup
install:
	@echo "🔧 Instalando dependências..."
	@make download-model || exit 1
	@echo "✅ Instalação concluída!"
'''

@pytest.fixture(autouse=True)
def mock_env():
    """Mock para variáveis de ambiente."""
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'OPENROUTER_API_KEY': 'test_key',
        'GEMINI_API_KEY': 'test_key',
        'ANTHROPIC_API_KEY': 'test_key',
        'DEFAULT_MODEL': 'gpt-3.5-turbo',
        'ELEVATION_MODEL': 'gpt-4',
        'MAX_RETRIES': '3',
        'MODEL_TIMEOUT': '120',
        'FALLBACK_ENABLED': 'true',
        'CACHE_ENABLED': 'false',
        'CACHE_TTL': '3600',
        'CACHE_DIR': '/tmp/cache'
    }):
        yield

@pytest.fixture
def mock_kernel_config():
    """Mock para configurações do kernel."""
    with patch("src.core.kernel.load_config") as mock:
        mock.return_value = {
            "required_vars": {
                "cli": ["OPENAI_API_KEY"],
                "github": ["GITHUB_TOKEN"],
                "publish": ["PYPI_TOKEN"]
            }
        }
        yield mock

@pytest.fixture
def mock_db_manager():
    """Mock para o DatabaseManager."""
    mock = MagicMock()
    return mock

@pytest.fixture
def mock_model_manager():
    """Mock para o ModelManager."""
    mock = MagicMock()
    mock.generate_response = MagicMock()
    return mock

@pytest.fixture
def mock_orchestrator(mock_model_manager, mock_db_manager, mock_kernel_config):
    """Mock do AgentOrchestrator."""
    orchestrator = AgentOrchestrator(mock_model_manager)
    orchestrator.db = mock_db_manager
    return orchestrator

@pytest.fixture
def mock_get_orchestrator(mock_model_manager, mock_db_manager, mock_kernel_config):
    """Mock para a função get_orchestrator."""
    with patch("src.cli.get_orchestrator") as mock:
        mock.return_value = mock_orchestrator(mock_model_manager, mock_db_manager, mock_kernel_config)
        yield mock

@pytest.fixture
def mock_validate_env():
    """Mock para a função validate_env."""
    with patch("src.cli.validate_env") as mock:
        yield mock

@pytest.fixture
def mock_get_env_status():
    """Mock para a função get_env_status."""
    with patch("src.cli.get_env_status") as mock:
        mock.return_value = {"status": "ok", "message": "Ambiente configurado"}
        yield mock

@pytest.fixture
def mock_mcp_handler():
    """Mock do MCPHandler."""
    with patch("src.mcp.MCPHandler") as mock:
        mock_handler = Mock()
        mock_handler.run = Mock()
        mock.return_value = mock_handler
        yield mock_handler

@pytest.fixture
def db_manager():
    """Fixture para o DatabaseManager."""
    return DatabaseManager(":memory:")

@pytest.fixture
def input_guardrail(mock_model_manager):
    """Fixture para o InputGuardrail."""
    return InputGuardrail(mock_model_manager)

@pytest.fixture
def output_guardrail(mock_model_manager):
    """Fixture para o OutputGuardrail."""
    return OutputGuardrail(mock_model_manager)

@pytest.fixture(autouse=True)
def setup_db_dir(tmp_path):
    """Configura diretório temporário para o banco de dados."""
    os.environ["DB_PATH"] = str(tmp_path / "test.db")
    yield
    if os.path.exists(os.environ["DB_PATH"]):
        os.remove(os.environ["DB_PATH"])

# Testes do CLI
def test_feature_command_success(mock_get_orchestrator, mock_validate_env, capsys, mock_env, mock_kernel_config):
    """Testa o comando feature com sucesso."""
    # Configurando o resultado esperado
    result = AgentResult(
        output="Resposta do agente para feature de login",
        items=[{"type": "feature", "content": "Login implementado com sucesso"}],
        guardrails=[],
        raw_responses=[{"id": "test-login", "response": {"text": "Login implementado"}}]
    )
    mock_get_orchestrator.execute.return_value = result
    
    # Executa comando
    os.system("make dev prompt-tdd=\"Login\" format=json")
    
    # Verifica saída
    captured = capsys.readouterr()
    assert "🛠️ Executando CLI em modo desenvolvimento..." in captured.out
    assert "Login implementado com sucesso" in captured.out

def test_feature_command_markdown_output(mock_get_orchestrator, mock_validate_env, capsys, mock_env, mock_kernel_config):
    """Testa o comando feature com saída em markdown."""
    # Configurando o resultado esperado
    markdown_content = "# Feature: Login\n\n## Testes\n- Test 1"
    result = AgentResult(
        output=markdown_content,
        items=[{"type": "feature", "content": markdown_content}],
        guardrails=[],
        raw_responses=[{"id": "test-md", "response": {"text": markdown_content}}]
    )
    mock_get_orchestrator.execute.return_value = result
    
    # Executa comando
    os.system("make dev prompt-tdd=\"Login\" format=markdown")
    
    # Verifica saída
    captured = capsys.readouterr()
    assert "🛠️ Executando CLI em modo desenvolvimento..." in captured.out
    assert "# Feature: Login" in captured.out

def test_feature_command_error(mock_get_orchestrator, mock_validate_env, capsys, mock_env, mock_kernel_config):
    """Testa o comando feature com erro."""
    # Configura erro
    mock_get_orchestrator.execute.side_effect = ValueError("Erro de teste")
    
    # Executa comando
    os.system("make dev prompt-tdd=\"Login\" format=json")
    
    # Verifica saída de erro
    captured = capsys.readouterr()
    assert "❌ Erro: Erro de teste" in captured.err

def test_output_guardrail_missing_fields(output_guardrail, mock_model_manager, mock_kernel_config):
    """Testa tratamento de campos ausentes no guardrail de saída."""
    # Prepara dados de teste
    output = json.dumps({
        "name": "Sistema de Login",
        "description": "Sistema de autenticação"
    })
    context = "Criar sistema de login"

    # Configura o mock para retornar um JSON inválido
    mock_model_manager.generate_response.return_value = json.dumps({
        "name": "Sistema de Login",
        "description": "Sistema de autenticação"
    })

    # Executa teste
    result = output_guardrail.process(output, context)

    assert result["status"] == "error"
    assert "Campos obrigatórios ausentes" in result["error"]

def test_agent_orchestrator_execute_error(mock_orchestrator, mock_model_manager, mock_kernel_config):
    """Testa tratamento de erro na execução do orquestrador."""
    # Configura o mock para retornar um JSON inválido
    mock_model_manager.generate_response.return_value = "resposta inválida"

    # Configura o mock do orquestrador
    mock_orchestrator.model_manager = mock_model_manager

    # Executa teste
    prompt = "Criar sistema de login"

    # Verifica se a exceção é lançada com a mensagem correta
    with pytest.raises(ValueError) as exc_info:
        mock_orchestrator.execute(prompt)

    assert "Campos obrigatórios ausentes" in str(exc_info.value)

