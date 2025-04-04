"""
Testes para o módulo CLI.
"""
from unittest.mock import Mock, patch
import os

import pytest
from typer.testing import CliRunner

from src.cli import app

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
def mock_models():
    """Mock do ModelManager."""
    with patch("src.core.ModelManager") as mock:
        mock_instance = Mock()
        mock_instance.configure = Mock()
        mock_instance.get_available_models = Mock(return_value=["gpt-4", "gpt-3.5"])
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_orchestrator(mock_models):
    """Mock do AgentOrchestrator."""
    with patch("src.app.AgentOrchestrator") as mock:
        mock_instance = Mock()
        mock_instance.models = mock_models
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

def test_feature_command_success():
    """Testa o comando feature com sucesso."""
    with patch('src.cli.validate_env') as mock_validate, \
         patch('src.cli.AgentOrchestrator') as mock_agent:
        
        mock_agent.return_value.execute.return_value = "Resposta do agente"
        result = runner.invoke(app, ["feature", "test", "--format", "markdown"])
        
        assert result.exit_code == 0
        mock_validate.assert_called_once()
        mock_agent.return_value.execute.assert_called_once()

def test_feature_command_markdown_output():
    """Testa o comando feature com saída em markdown."""
    with patch('src.cli.validate_env'), \
         patch('src.cli.AgentOrchestrator') as mock_agent:
        
        mock_agent.return_value.execute.return_value = "# Título\nConteúdo"
        result = runner.invoke(app, ["feature", "test", "--format", "markdown"])
        
        assert result.exit_code == 0
        assert "# Título" in result.stdout

def test_feature_command_error():
    """Testa o comando feature com erro."""
    with patch('src.cli.validate_env') as mock_validate:
        mock_validate.side_effect = Exception("Erro de validação")
        result = runner.invoke(app, ["feature", "test"])
        
        assert result.exit_code == 1

def test_status_command_success():
    """Testa o comando status com sucesso."""
    with patch('src.cli.get_env_status') as mock_status:
        mock_status.return_value = {
            "all_required_set": True,
            "required": {"OPENAI_API_KEY": True},
            "optional": {}
        }
        result = runner.invoke(app, ["status"])
        
        assert result.exit_code == 0
        mock_status.assert_called_once()

def test_status_command_error():
    """Testa o comando status com erro."""
    with patch('src.cli.get_env_status') as mock_status:
        mock_status.side_effect = Exception("Erro ao obter status")
        result = runner.invoke(app, ["status"])
        
        assert result.exit_code == 1

def test_mcp_command_feature():
    """Testa o comando mcp com feature."""
    with patch('src.cli.validate_env'), \
         patch('src.cli.MCPHandler') as mock_mcp:
        
        result = runner.invoke(app, ["mcp", "test", "--format", "markdown"])
        
        assert result.exit_code == 0
        mock_mcp.assert_called_once()

def test_mcp_command_error():
    """Testa o comando mcp com erro."""
    with patch('src.cli.validate_env'), \
         patch('src.cli.MCPHandler') as mock_mcp:
        
        mock_mcp.side_effect = Exception("Erro ao inicializar MCP")
        result = runner.invoke(app, ["mcp", "test"])
        
        assert result.exit_code == 1

def test_mcp_command_no_api_key():
    """Testa o comando mcp sem API key."""
    with patch.dict(os.environ, {}, clear=True):
        result = runner.invoke(app, ["mcp", "test"])
        assert result.exit_code == 1

def test_feature_command_address_requirements():
    """Testa o comando feature com requisitos de endereço."""
    with patch('src.cli.validate_env'), \
         patch('src.cli.AgentOrchestrator') as mock_agent:
        
        mock_agent.return_value.execute.return_value = """
        Requisitos para cadastro de endereço:
        1. Nome completo
        2. Endereço completo
        3. CEP
        4. Cidade/Estado
        """
        result = runner.invoke(app, ["feature", "Cadastro de endereços", "--format", "markdown"])
        
        assert result.exit_code == 0
        assert "Requisitos para cadastro" in result.stdout

def test_feature_command_with_cache():
    """Testa o comando feature com cache."""
    with patch('src.cli.validate_env'), \
         patch('src.cli.AgentOrchestrator') as mock_agent, \
         patch('src.core.models.ModelManager') as mock_model:
        
        # Simula cache hit
        mock_model.return_value.generate.return_value = ("Resposta do cache", {"cached": True})
        mock_agent.return_value.execute.return_value = "Resposta do cache"
        
        result = runner.invoke(app, ["feature", "test cached", "--format", "markdown"])
        
        assert result.exit_code == 0
        assert "Resposta do cache" in result.stdout 