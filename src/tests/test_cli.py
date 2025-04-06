"""
Testes para o módulo CLI.
"""
import os
from unittest.mock import patch, mock_open, Mock, MagicMock
import sys

import pytest

from src.cli import app
from src.app import AgentResult
from src.scripts.utils_view_logs import main as view_logs_main

@pytest.fixture
def mock_env():
    """Mock das variáveis de ambiente."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        yield

@pytest.fixture
def mock_kernel_config():
    """Mock para a configuração do kernel."""
    kernel_config = {
        "required_vars": {
            "cli": ["OPENAI_API_KEY"]
        }
    }
    
    m = mock_open(read_data=str(kernel_config))
    with patch("builtins.open", m):
        with patch("src.core.kernel.yaml.safe_load", return_value=kernel_config):
            yield

@pytest.fixture
def mock_db_manager():
    """Mock do DatabaseManager."""
    with patch('src.core.db.DatabaseManager') as mock:
        mock_instance = Mock()
        mock_instance.log_run = Mock(return_value=1)  # Retorna ID 1 para os registros
        
        # Mock para get_run_history com diferentes comportamentos
        def get_history_mock(*args, **kwargs):
            if 'run_id' in kwargs and kwargs['run_id'] == 1:
                return [{
                    "id": 1,
                    "session_id": "test-session",
                    "input": "Test input",
                    "final_output": "Test output",
                    "last_agent": "OpenAI",
                    "output_type": "json",
                    "timestamp": "2024-04-04 12:00:00",
                    "items": [],
                    "guardrails": [],
                    "raw_responses": [{"id": "test", "response": "Test response"}]
                }]
            return []
            
        mock_instance.get_run_history = Mock(side_effect=get_history_mock)
        
        # Mock para config com directories
        mock_instance.config = {
            "directories": {"logs": "logs"},
            "database": {"default_path": "logs/agent_logs.db", "history_limit": 10}
        }
        
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_orchestrator(mock_db_manager):
    """Mock do AgentOrchestrator."""
    with patch('src.app.AgentOrchestrator') as mock:
        mock_instance = Mock()
        mock_instance.models = Mock()
        mock_instance.db = mock_db_manager
        
        # Configuração padrão do retorno do execute
        result = AgentResult(
            output="Resposta padrão do agente",
            items=[{"type": "feature", "content": "Resposta padrão"}],
            guardrails=[],
            raw_responses=[{"id": "test", "response": {"text": "Resposta padrão"}}]
        )
        mock_instance.execute.return_value = result
        
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_validate_env():
    """Mock da função validate_env."""
    with patch("src.cli.validate_env") as mock:
        yield mock

@pytest.fixture
def mock_get_orchestrator(mock_orchestrator):
    """Mock da função get_orchestrator."""
    with patch("src.cli.get_orchestrator") as mock:
        mock.return_value = mock_orchestrator
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
def mock_mcp_handler():
    """Mock do MCPHandler."""
    with patch("src.mcp.MCPHandler") as mock:
        mock_handler = Mock()
        mock_handler.run = Mock()
        mock.return_value = mock_handler
        yield mock_handler

@pytest.fixture
def mock_model_manager():
    """Mock do ModelManager."""
    with patch("src.core.models.ModelManager") as mock:
        mock_instance = MagicMock()
        mock_instance.get_available_models = Mock(return_value=["gpt-4", "gpt-3.5-turbo"])
        mock.return_value = mock_instance
        yield mock_instance

def test_feature_command_success(mock_get_orchestrator, mock_validate_env, capsys, mock_env, mock_kernel_config):
    """Testa o comando feature com sucesso."""
    # Configurando o resultado esperado
    result = AgentResult(
        output="Resposta do agente para feature de login",
        items=[{"type": "feature", "content": "Login implementado com sucesso"}],
        guardrails=[],
        raw_responses=[{"id": "test-login", "response": {"text": "Login implementado"}}]
    )
    mock_get_orchestrator.return_value.execute.return_value = result
    
    # Execução do comando
    with pytest.raises(SystemExit) as exc_info:
        app(["feature", "Criar sistema de login"])
        
    # Verificações
    assert exc_info.value.code == 0
    mock_validate_env.assert_called_once()
    mock_get_orchestrator.assert_called_once()
    mock_get_orchestrator.return_value.execute.assert_called_once()
    
    # Verifica saída
    captured = capsys.readouterr()
    assert "Resposta do agente para feature de login" in captured.out

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
    mock_get_orchestrator.return_value.execute.return_value = result
    
    # Execução do comando
    with pytest.raises(SystemExit) as exc_info:
        app(["feature", "Criar login", "--format", "markdown"])
        
    # Verificações
    assert exc_info.value.code == 0
    
    # Verifica saída
    captured = capsys.readouterr()
    assert "Feature: Login" in captured.out
    # O rich.Markdown formata o texto, então o '##' é convertido em outro formato
    assert "Testes" in captured.out
    assert "Test 1" in captured.out

def test_feature_command_error(mock_validate_env, capsys, mock_env, mock_kernel_config):
    """Testa o comando feature com erro."""
    # Configurando erro
    mock_validate_env.side_effect = Exception("Erro de validação")

    # Execução do comando
    with pytest.raises(SystemExit) as exc_info:
        app(["feature", "Criar login"])
        
    # Verificações
    assert exc_info.value.code == 1
    
    # Verifica mensagem de erro
    captured = capsys.readouterr()
    assert "Erro ao processar comando" in captured.err

def test_status_command_success(mock_get_env_status, capsys, mock_env, mock_kernel_config):
    """Testa o comando status com sucesso."""
    # Mock para ModelManager diretamente no cli.py
    with patch("src.cli.ModelManager") as mock_model:
        mock_instance = MagicMock()
        # Configura o retorno para get_available_models
        mock_instance.get_available_models.return_value = ["gpt-4", "gpt-3.5-turbo"]
        mock_model.return_value = mock_instance
        
        # Execução do comando
        with pytest.raises(SystemExit) as exc_info:
            app(["status"])
            
        # Verificações
        assert exc_info.value.code == 0
        mock_get_env_status.assert_called_once()
        
        # Verifica saída
        captured = capsys.readouterr()
        assert "OPENAI_API_KEY" in captured.out

def test_status_command_error(mock_get_env_status, capsys, mock_env, mock_kernel_config):
    """Testa o comando status com erro."""
    # Configurando erro
    mock_get_env_status.side_effect = Exception("Erro ao obter status")

    # Execução do comando
    with pytest.raises(SystemExit) as exc_info:
        app(["status"])
        
    # Verificações
    assert exc_info.value.code == 1
    
    # Verifica mensagem de erro
    captured = capsys.readouterr()
    assert "Erro ao processar comando" in captured.err

def test_mcp_command_feature(mock_mcp_handler, capsys, mock_env, mock_kernel_config):
    """Testa o comando mcp com feature."""
    # Execução do comando
    with pytest.raises(SystemExit) as exc_info:
        app(["mcp", "test", "--format", "markdown"])
        
    # Verificações
    assert exc_info.value.code == 0
    mock_mcp_handler.run.assert_called_once()
    
    # Verifica saída
    captured = capsys.readouterr()
    assert "Executando CLI" in captured.out

def test_mcp_command_error(mock_env, mock_kernel_config, capsys):
    """Testa o comando mcp com erro."""
    with patch("src.mcp.MCPHandler") as mock_handler:
        # Configurando erro
        mock_handler.side_effect = Exception("Erro ao inicializar MCP")

        # Execução do comando
        with pytest.raises(SystemExit) as exc_info:
            app(["mcp", "test"])
            
        # Verificações
        assert exc_info.value.code == 1
        
        # Verifica mensagem de erro
        captured = capsys.readouterr()
        assert "Erro ao processar comando" in captured.err

def test_mcp_command_no_api_key(capsys):
    """Testa o comando mcp sem API key."""
    with patch.dict(os.environ, {}, clear=True):
        # Execução do comando
        with pytest.raises(SystemExit) as exc_info:
            app(["mcp", "test"])
            
        # Verificações
        assert exc_info.value.code == 1
        
        # Verifica mensagem de erro
        captured = capsys.readouterr()
        assert "Variáveis de ambiente obrigatórias não definidas" in captured.err

def test_feature_command_address_requirements(mock_get_orchestrator, mock_validate_env, capsys, mock_env, mock_kernel_config):
    """Testa o comando feature com requisitos de endereço."""
    # Conteúdo sobre requisitos de endereço
    address_content = """
    Requisitos para cadastro de endereço:
    1. Nome completo
    2. Endereço completo
    3. CEP
    4. Cidade/Estado
    """
    
    # Configurando o resultado esperado
    result = AgentResult(
        output=address_content,
        items=[{"type": "feature", "content": address_content}],
        guardrails=[],
        raw_responses=[{"id": "address-test", "response": {"text": address_content}}]
    )
    mock_get_orchestrator.return_value.execute.return_value = result
    
    # Execução do comando
    with pytest.raises(SystemExit) as exc_info:
        app(["feature", "Cadastro de endereços"])
        
    # Verificações
    assert exc_info.value.code == 0
    mock_validate_env.assert_called_once()
    
    # Verifica saída
    captured = capsys.readouterr()
    assert "Nome completo" in captured.out
    assert "Endereço completo" in captured.out
    assert "CEP" in captured.out

def test_feature_command_with_cache(mock_get_orchestrator, mock_validate_env, capsys, mock_env, mock_kernel_config):
    """Testa o comando feature com cache."""
    # Configurando o resultado esperado com metadados de cache
    cache_content = "Resposta do cache"
    result = AgentResult(
        output=cache_content,
        items=[{"type": "feature", "content": cache_content}],
        guardrails=[],
        raw_responses=[{
            "id": "cache-test",
            "response": {
                "text": cache_content,
                "cached": True,
                "model": "gpt-4"
            }
        }]
    )
    mock_get_orchestrator.return_value.execute.return_value = result
    
    # Execução do comando
    with pytest.raises(SystemExit) as exc_info:
        app(["feature", "test cached", "--format", "markdown"])
        
    # Verificações
    assert exc_info.value.code == 0
    
    # Verifica saída
    captured = capsys.readouterr()
    assert cache_content in captured.out

def test_view_logs_command(capsys, mock_db_manager):
    """Testa o comando de visualização de logs."""
    # Mock do sys.argv para simular argumentos da linha de comando
    with patch.object(sys, 'argv', ['utils_view_logs.py', '--limit', '5']):
        # Executa a função principal do visualizador de logs
        view_logs_main()
        
    # Verifica se a saída contém elementos esperados
    captured = capsys.readouterr()
    assert "Histórico de Execuções" in captured.out
    assert "Timestamp" in captured.out
    assert "Session" in captured.out
    assert "Agente" in captured.out

def test_view_logs_with_session_filter(capsys, mock_db_manager):
    """Testa o comando de logs com filtro de sessão."""
    # Mock do sys.argv para simular argumentos da linha de comando
    with patch.object(sys, 'argv', ['utils_view_logs.py', '--session', 'test123']):
        # Executa a função principal do visualizador de logs
        view_logs_main()
        
    # Verifica se a saída contém elementos esperados
    captured = capsys.readouterr()
    assert "Histórico de Execuções" in captured.out

def test_view_logs_with_id_details(capsys, mock_db_manager):
    """Testa o comando de logs mostrando detalhes de uma execução específica."""
    # Mock do sys.argv para simular argumentos da linha de comando
    with patch.object(sys, 'argv', ['utils_view_logs.py', '--id', '1']):
        # Executa a função principal do visualizador de logs
        view_logs_main()
        
    # Verifica se a saída contém elementos esperados
    captured = capsys.readouterr()
    assert "Execução" in captured.out
    assert "Input:" in captured.out 