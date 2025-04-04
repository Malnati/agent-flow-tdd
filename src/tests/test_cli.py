"""
Testes para o módulo CLI.
"""
import json
from unittest.mock import Mock, patch
import os

import pytest
from typer.testing import CliRunner

from src.cli import app
from src.app import AgentResult

# Setup
runner = CliRunner()

# Mock do SDK MCP
class MockMessage:
    def __init__(self, content, metadata):
        self.content = content
        self.metadata = metadata

class MockMCPHandler:
    def __init__(self):
        self.orchestrator = None
        self.hook = "/prompt-tdd"
    
    def initialize(self, api_key=None):
        pass
    
    def handle_message(self, message):
        pass
    
    def run(self):
        pass

@pytest.fixture
def mock_model_manager():
    """Mock do ModelManager."""
    with patch("src.core.ModelManager") as mock:
        mock_instance = Mock()
        mock_instance.configure = Mock()
        mock_instance.get_available_models = Mock(return_value=["gpt-4", "gpt-3.5"])
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_orchestrator(mock_model_manager):
    """Mock do AgentOrchestrator."""
    with patch("src.app.AgentOrchestrator") as mock:
        mock_instance = Mock()
        mock_instance.model_manager = mock_model_manager
        mock_instance.visualizer = Mock()
        mock_instance.execute = Mock(return_value=Mock(output="# Feature: Login"))
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_validate_env():
    """Mock da função validate_env."""
    with patch("src.cli.validate_env") as mock:
        yield mock

@pytest.fixture
def mock_get_env_status():
    """Mock da função get_env_status."""
    with patch("src.cli.get_env_status") as mock:
        mock.return_value = {
            "required": {"OPENAI_API_KEY": True},
            "optional": {"ELEVATION_MODEL": False}
        }
        yield mock

@pytest.fixture
def mock_mcp_sdk():
    """Mock do SDK MCP."""
    with patch("src.mcp.BaseMCPHandler") as mock:
        mock_handler = Mock()
        mock_handler.hook = "/prompt-tdd"
        mock_handler.initialize = Mock()
        mock_handler.run = Mock()
        mock.return_value = mock_handler
        yield mock

def test_feature_command_success(mock_model_manager, mock_orchestrator, mock_validate_env, capsys):
    """Testa o comando feature com sucesso."""
    # Setup
    mock_orchestrator.execute.return_value = Mock(
        output=json.dumps({
            "feature": "Login",
            "tests": ["test1"]
        })
    )

    with patch("src.cli.get_orchestrator", return_value=mock_orchestrator):
        # Execução
        with pytest.raises(SystemExit) as exc_info:
            app(["feature", "Criar sistema de login"])
            
        # Verificações
        assert exc_info.value.code == 0
        mock_validate_env.assert_called_once()
        captured = capsys.readouterr()
        assert "🛠️ Executando CLI em modo desenvolvimento..." in captured.out

def test_feature_command_markdown_output(mock_model_manager, mock_orchestrator, mock_validate_env, capsys):
    """Testa o comando feature com saída em markdown."""
    # Setup
    mock_orchestrator.execute.return_value = Mock(
        output="# Feature: Login\n\n## Testes\n- Test 1"
    )

    with patch("src.cli.get_orchestrator", return_value=mock_orchestrator):
        # Execução
        with pytest.raises(SystemExit) as exc_info:
            app(["feature", "Criar login", "--format", "markdown"])
            
        # Verificações
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "🛠️ Executando CLI em modo desenvolvimento..." in captured.out

def test_feature_command_error(mock_model_manager, mock_orchestrator, mock_validate_env, capsys):
    """Testa o comando feature com erro."""
    # Setup
    mock_validate_env.side_effect = Exception("Erro de validação")

    with patch("src.cli.get_orchestrator", return_value=mock_orchestrator):
        # Execução
        with pytest.raises(SystemExit) as exc_info:
            app(["feature", "Criar login"])
            
        # Verificações
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Erro ao processar comando" in captured.err

def test_status_command_success(mock_model_manager, mock_get_env_status, capsys):
    """Testa o comando status com sucesso."""
    # Setup
    mock_model_manager.get_available_models.return_value = ["gpt-4", "gpt-3.5"]

    with patch("src.cli.ModelManager", return_value=mock_model_manager):
        # Execução
        with pytest.raises(SystemExit) as exc_info:
            app(["status"])
            
        # Verificações
        assert exc_info.value.code == 0
        mock_get_env_status.assert_called_once()
        mock_model_manager.get_available_models.assert_called_once()
        captured = capsys.readouterr()
        assert "environment" in captured.out
        assert "models" in captured.out

def test_status_command_error(mock_model_manager, mock_get_env_status, capsys):
    """Testa o comando status com erro."""
    # Setup
    mock_get_env_status.side_effect = Exception("Erro ao obter status")

    with patch("src.cli.ModelManager", return_value=mock_model_manager):
        # Execução
        with pytest.raises(SystemExit) as exc_info:
            app(["status"])
            
        # Verificações
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Erro ao processar comando" in captured.err

def test_mcp_command_feature(mock_orchestrator, capsys, monkeypatch, mock_mcp_sdk):
    """Testa o comando MCP processando uma feature."""
    # Setup
    input_data = {
        "content": "Criar login",
        "metadata": {
            "type": "feature",
            "options": {
                "model": "gpt-4-turbo",
                "temperature": 0.7
            }
        }
    }

    # Simula entrada stdin
    input_lines = [json.dumps(input_data) + "\n", ""]
    input_iter = iter(input_lines)
    monkeypatch.setattr("sys.stdin.readline", lambda: next(input_iter))

    # Configura mock do handler
    mock_handler = mock_mcp_sdk.return_value
    mock_handler.initialize.return_value = None
    mock_handler.run.side_effect = lambda: None

    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), \
         patch("src.mcp.MCPHandler", return_value=mock_handler):

        # Execução
        with pytest.raises(SystemExit) as exc_info:
            app(["mcp"])
            
        # Verificações
        assert exc_info.value.code == 0
        mock_handler.initialize.assert_called_once_with(api_key="test-key")
        captured = capsys.readouterr()
        assert "🛠️ Executando CLI em modo desenvolvimento..." in captured.out

def test_mcp_command_error(mock_orchestrator, capsys, monkeypatch, mock_mcp_sdk):
    """Testa o comando MCP com erro."""
    # Setup
    with patch("src.mcp.MCPHandler") as mock_handler:
        mock_handler.side_effect = Exception("Erro ao inicializar MCP")

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            # Execução
            with pytest.raises(SystemExit) as exc_info:
                app(["mcp"])
                
            # Verificações
            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Erro ao processar comando" in captured.err

def test_mcp_command_no_api_key(mock_orchestrator, capsys, monkeypatch, mock_mcp_sdk):
    """Testa o comando MCP sem chave de API."""
    # Setup
    original_env = dict(os.environ)
    try:
        # Preserva outras variáveis de ambiente, apenas remove OPENAI_API_KEY
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
            
        # Execução
        with pytest.raises(SystemExit) as exc_info:
            app(["mcp"])
            
        # Verificações
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Variáveis de ambiente obrigatórias não definidas" in captured.err
    finally:
        # Restaura o ambiente original
        os.environ.clear()
        os.environ.update(original_env)

def test_feature_command_address_requirements(mock_model_manager, mock_orchestrator, mock_validate_env, capsys):
    """Testa o comando feature via terminal para requisitos de endereço."""
    # Setup
    expected_result = {
        "feature": "Gerenciamento de Endereços",
        "acceptance_criteria": [
            "Deve permitir cadastro de endereços com CEP (Brasil) e ZipCode (EUA)",
            "Deve integrar com API de busca de CEP para autopreenchimento",
            "Deve integrar com API de ZipCode US para autopreenchimento",
            "Deve permitir edição de endereços cadastrados",
            "Deve permitir listagem de endereços com paginação e filtros"
        ],
        "test_scenarios": [
            "Cadastro com CEP válido brasileiro",
            "Cadastro com ZipCode válido americano",
            "Tentativa de cadastro com CEP inválido",
            "Tentativa de cadastro com ZipCode inválido",
            "Edição de endereço existente",
            "Listagem com filtro por país",
            "Paginação de resultados"
        ],
        "integrations": [
            {"name": "ViaCEP API", "type": "CEP", "country": "BR"},
            {"name": "USPS API", "type": "ZipCode", "country": "US"}
        ],
        "complexity": 4
    }

    mock_orchestrator.execute.return_value = Mock(output=json.dumps(expected_result))

    with patch("src.cli.get_orchestrator", return_value=mock_orchestrator):
        # Execução
        with pytest.raises(SystemExit) as exc_info:
            app(["feature", "Cadastro de endereços"])
            
        # Verificações
        assert exc_info.value.code == 0
        mock_validate_env.assert_called_once()
        captured = capsys.readouterr()
        assert "🛠️ Executando CLI em modo desenvolvimento..." in captured.out 

def test_feature_command_with_cache(mock_model_manager, mock_orchestrator, mock_validate_env, capsys):
    """Testa o comando feature com resposta em cache."""
    # Setup
    cached_response = {
        "text": "# Feature: Login\n\n## Testes\n- Test 1",
        "metadata": {
            "model": "gpt-3.5-turbo",
            "provider": "openai",
            "finish_reason": "stop",
            "created": 1234567890,
            "id": "test-id"
        }
    }

    mock_orchestrator.execute.return_value = AgentResult(
        output=cached_response["text"],
        items=[],
        guardrails=[],
        raw_responses=[{
            "id": cached_response["metadata"]["id"],
            "response": cached_response["metadata"]
        }]
    )

    with patch("src.cli.get_orchestrator", return_value=mock_orchestrator):
        # Execução
        with pytest.raises(SystemExit) as exc_info:
            app(["feature", "Criar login", "--format", "markdown"])
            
        # Verificações
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "🛠️ Executando CLI em modo desenvolvimento..." in captured.out
        assert "Feature: Login" in captured.out
        assert "Test 1" in captured.out 