"""
Testes unificados para o projeto.
Inclui testes de CLI, banco de dados e download de modelos.
"""

import json
import sqlite3
import os
import shutil
from unittest.mock import patch, mock_open, Mock, MagicMock
import yaml
from pathlib import Path

import pytest

from src.cli import app
from src.app import AgentResult
from src.core.db import DatabaseManager
from src.core.models import ModelManager

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

# Fixtures compartilhadas
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
        mock_instance.log_run = Mock(return_value=TEST_CONFIG['database']['test_data']['mock_run']['id'])
        
        # Mock para get_run_history com diferentes comportamentos
        def get_history_mock(*args, **kwargs):
            if 'run_id' in kwargs:
                if kwargs['run_id'] == 1:  # Para o teste test_view_logs_with_id_details
                    return [{
                        'id': 1,
                        'session_id': 'test-session',
                        'timestamp': '2024-04-06T20:00:00',
                        'input': 'Test input',
                        'final_output': 'Test output',
                        'output_type': 'markdown',
                        'last_agent': 'OpenAI',
                        'items': [{'item_type': 'test', 'source_agent': 'test', 'target_agent': 'test', 'raw_item': 'test'}],
                        'guardrails': [{'guardrail_type': 'test', 'results': 'test'}],
                        'raw_responses': [{'id': 1, 'response': 'test'}]
                    }]
                elif kwargs['run_id'] == TEST_CONFIG['database']['test_data']['mock_run']['id']:
                    return [TEST_CONFIG['database']['test_data']['mock_run']]
            return []
            
        mock_instance.get_run_history = Mock(side_effect=get_history_mock)
        
        # Mock para config com directories
        mock_instance.config = {
            "directories": {"logs": "logs"},
            "database": {"default_path": "logs/agent_logs.db", "history_limit": 10}
        }
        
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
    """Mock do ModelManager para testes."""
    with patch("src.core.models.ModelManager") as mock:
        # Configura o mock do TinyLLaMA
        mock._get_provider.return_value = "tinyllama"
        mock.tinyllama_model = MagicMock()
        mock.tinyllama_model.create_chat_completion.return_value = {
            "choices": [{"message": {"content": "Resposta de teste"}}]
        }
        yield mock

@pytest.fixture
def db_manager():
    """Fixture que fornece um DatabaseManager com banco em memória."""
    manager = DatabaseManager(":memory:")
    yield manager
    manager.close()

@pytest.fixture
def test_env(tmp_path):
    """Cria um ambiente temporário para testes."""
    original_dir = os.getcwd()
    models_dir = tmp_path / "models"
    models_dir.mkdir(exist_ok=True)
    
    # Cria o Makefile no diretório temporário
    makefile_path = tmp_path / "Makefile"
    makefile_path.write_text(MAKEFILE_CONTENT)
    
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_dir)

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
    mock_validate_env.assert_called_once()
    
    # Verifica mensagem de erro
    captured = capsys.readouterr()
    assert "Erro de validação" in captured.err

# Testes do Banco de Dados
def test_create_tables(db_manager):
    """Testa a criação das tabelas."""
    cursor = db_manager.conn.cursor()
    
    # Verifica tabelas criadas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    
    # Verifica se todas as tabelas requeridas foram criadas
    for table in TEST_CONFIG['database']['required_tables']:
        assert table in tables

def test_log_run(db_manager):
    """Testa o registro de uma execução."""
    run_id = db_manager.log_run(
        session_id="test-session",
        input="test input",
        last_agent="TestAgent",
        output_type="json",
        final_output='{"result": "test"}'
    )
    
    cursor = db_manager.conn.cursor()
    cursor.execute("SELECT * FROM agent_runs WHERE id = ?", (run_id,))
    row = cursor.fetchone()
    
    assert row is not None
    assert row[2] == "test-session"  # session_id
    assert row[3] == "test input"    # input
    assert row[4] == "TestAgent"     # last_agent
    assert row[5] == "json"          # output_type
    assert row[6] == '{"result": "test"}'  # final_output

def test_log_run_item(db_manager):
    """Testa o registro de um item gerado."""
    run_id = db_manager.log_run("test-session", "test input")
    
    db_manager.log_run_item(
        run_id=run_id,
        item_type="MessageOutput",
        raw_item={"content": "test message"},
        source_agent="SourceAgent",
        target_agent="TargetAgent"
    )
    
    cursor = db_manager.conn.cursor()
    cursor.execute("SELECT * FROM run_items WHERE run_id = ?", (run_id,))
    row = cursor.fetchone()
    
    assert row is not None
    assert row[1] == run_id  # run_id
    assert row[3] == "MessageOutput"  # item_type
    assert json.loads(row[4]) == {"content": "test message"}  # raw_item
    assert row[5] == "SourceAgent"  # source_agent
    assert row[6] == "TargetAgent"  # target_agent

def test_log_guardrail_results(db_manager):
    """Testa o registro de resultados de guardrails."""
    run_id = db_manager.log_run("test-session", "test input")
    
    db_manager.log_guardrail_results(
        run_id=run_id,
        guardrail_type="input",
        results={"passed": True, "message": "All good"}
    )
    
    cursor = db_manager.conn.cursor()
    cursor.execute("SELECT * FROM guardrail_results WHERE run_id = ?", (run_id,))
    row = cursor.fetchone()
    
    assert row is not None
    assert row[1] == run_id  # run_id
    assert row[3] == "input"  # guardrail_type
    assert json.loads(row[4]) == {"passed": True, "message": "All good"}  # results

def test_log_raw_response(db_manager):
    """Testa o registro de respostas brutas do LLM."""
    run_id = db_manager.log_run("test-session", "test input")
    
    db_manager.log_raw_response(
        run_id=run_id,
        response={"content": "test response", "model": "gpt-3.5-turbo"}
    )
    
    cursor = db_manager.conn.cursor()
    cursor.execute("SELECT * FROM raw_responses WHERE run_id = ?", (run_id,))
    row = cursor.fetchone()
    
    assert row is not None
    assert row[1] == run_id  # run_id
    assert json.loads(row[3]) == {  # response
        "content": "test response",
        "model": "gpt-3.5-turbo"
    }

def test_get_run_history(db_manager):
    """Testa a recuperação do histórico de execuções."""
    # Cria algumas execuções
    run_id1 = db_manager.log_run(
        session_id="session1",
        input="input1",
        last_agent="Agent1",
        output_type="json",
        final_output='{"result": 1}'
    )
    run_id2 = db_manager.log_run(
        session_id="session2",
        input="input2",
        last_agent="Agent2",
        output_type="json",
        final_output='{"result": 2}'
    )
    
    # Adiciona itens, guardrails e respostas
    db_manager.log_run_item(run_id1, "MessageOutput", {"content": "msg1"})
    db_manager.log_guardrail_results(run_id1, "input", {"passed": True})
    db_manager.log_raw_response(run_id1, {"content": "raw1"})
    
    db_manager.log_run_item(run_id2, "MessageOutput", {"content": "msg2"})
    db_manager.log_guardrail_results(run_id2, "output", {"passed": False})
    db_manager.log_raw_response(run_id2, {"content": "raw2"})
    
    # Busca histórico
    history = db_manager.get_run_history(limit=2)
    
    assert len(history) == 2
    assert history[0]["session_id"] == "session2"
    assert history[1]["session_id"] == "session1"
    
    # Verifica itens relacionados
    assert len(history[0]["items"]) == 1
    assert len(history[0]["guardrails"]) == 1
    assert len(history[0]["raw_responses"]) == 1

def test_invalid_guardrail_type(db_manager):
    """Testa validação do tipo de guardrail."""
    run_id = db_manager.log_run("test-session", "test input")
    
    with pytest.raises(sqlite3.IntegrityError):
        db_manager.log_guardrail_results(
            run_id=run_id,
            guardrail_type="invalid",
            results={"passed": True}
        )

def test_file_creation(tmp_path):
    """Testa criação do arquivo de banco de dados."""
    db_path = tmp_path / "test.db"
    manager = DatabaseManager(str(db_path))
    
    assert db_path.exists()
    manager.close()

def test_connection_error():
    """Testa erro de conexão com banco."""
    with patch("sqlite3.connect") as mock_connect:
        mock_connect.side_effect = sqlite3.Error("Connection error")
        
        with pytest.raises(sqlite3.Error):
            DatabaseManager(":memory:")

def test_db_init_command(tmp_path):
    """Testa o comando db-init do Makefile."""
    # Configura ambiente de teste
    test_db_path = tmp_path / "logs" / "agent_logs.db"
    os.makedirs(tmp_path / "logs", exist_ok=True)
    
    with patch.dict(os.environ, {"PYTHONPATH": str(tmp_path)}):
        # Inicializa banco de dados
        manager = DatabaseManager(str(test_db_path))
        
        # Verifica se o arquivo foi criado
        assert test_db_path.exists()
        manager.close()

def test_model_cache(db_manager):
    """Testa o cache de respostas do modelo no banco de dados."""
    # Testa salvamento no cache
    cache_key = "test_key"
    response = "test response"
    metadata = {"model": "test-model", "temperature": 0.7}
    
    db_manager.save_to_cache(cache_key, response, metadata)
    
    # Verifica se foi salvo
    cursor = db_manager.conn.cursor()
    cursor.execute("SELECT * FROM model_cache WHERE cache_key = ?", (cache_key,))
    row = cursor.fetchone()
    
    assert row is not None
    assert row[1] == cache_key  # cache_key
    assert json.loads(row[2]) == response  # response
    assert json.loads(row[3]) == metadata  # metadata
    
    # Testa recuperação do cache
    cached = db_manager.get_cached_response(cache_key, ttl=3600)
    assert cached is not None
    assert cached[0] == response
    assert cached[1] == metadata
    
    # Testa expiração do cache
    cached = db_manager.get_cached_response(cache_key, ttl=0)
    assert cached is None
    
    # Verifica se foi removido do banco
    cursor.execute("SELECT COUNT(*) FROM model_cache WHERE cache_key = ?", (cache_key,))
    count = cursor.fetchone()[0]
    assert count == 0

def test_model_cache_update(db_manager):
    """Testa atualização de entrada no cache."""
    cache_key = "test_key"
    
    # Primeira entrada
    db_manager.save_to_cache(cache_key, "response1", {"version": 1})
    
    # Segunda entrada com mesma chave
    db_manager.save_to_cache(cache_key, "response2", {"version": 2})
    
    # Verifica se só existe uma entrada
    cursor = db_manager.conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM model_cache WHERE cache_key = ?", (cache_key,))
    count = cursor.fetchone()[0]
    assert count == 1
    
    # Verifica se é a entrada mais recente
    cached = db_manager.get_cached_response(cache_key, ttl=3600)
    assert cached is not None
    assert cached[0] == "response2"
    assert cached[1] == {"version": 2}

def test_model_cache_unique_index(db_manager):
    """Testa o índice único na chave de cache."""
    cache_key = "test_key"
    
    # Primeira inserção
    db_manager.save_to_cache(cache_key, "response1", {"version": 1})
    
    # Segunda inserção com mesma chave (deve substituir a primeira)
    db_manager.save_to_cache(cache_key, "response2", {"version": 2})
    
    # Verifica se só existe uma entrada
    cursor = db_manager.conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM model_cache")
    total = cursor.fetchone()[0]
    assert total == 1

# Testes de Download do Modelo
def test_download_model_command(test_env, capfd):
    """Testa o comando de download do modelo."""
    # Executa o comando make download-model
    result = os.system("make download-model")
    captured = capfd.readouterr()
    
    # Verifica se o comando foi executado com sucesso
    assert result == 0, "O comando download-model falhou"
    
    # Verifica se o diretório models foi criado
    assert (test_env / "models").exists(), "Diretório models não foi criado"
    
    # Verifica se o arquivo do modelo existe
    model_file = test_env / "models" / "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
    assert model_file.exists(), "Arquivo do modelo não foi baixado"
    
    # Verifica as mensagens de log
    assert "📥 Baixando modelo TinyLLaMA..." in captured.out
    assert "✅ Download concluído" in captured.out or "✅ Modelo já existe" in captured.out

def test_download_model_idempotent(test_env, capfd):
    """Testa se o comando é idempotente (não baixa novamente se já existir)."""
    # Primeira execução
    os.system("make download-model")
    capfd.readouterr()  # Limpa o buffer
    
    # Segunda execução
    result = os.system("make download-model")
    captured = capfd.readouterr()
    
    # Verifica se o comando foi executado com sucesso
    assert result == 0, "O comando download-model falhou na segunda execução"
    
    # Verifica se a mensagem de modelo existente aparece
    assert "✅ Modelo já existe" in captured.out

def test_download_model_creates_directory(test_env):
    """Testa se o comando cria o diretório models se não existir."""
    # Remove o diretório models se existir
    models_dir = test_env / "models"
    if models_dir.exists():
        shutil.rmtree(models_dir)
    
    # Executa o comando
    result = os.system("make download-model")
    
    # Verifica se o diretório foi criado
    assert models_dir.exists(), "Diretório models não foi criado"
    assert result == 0, "O comando download-model falhou"

def test_download_model_handles_failure(test_env, capfd):
    """Testa se o comando lida corretamente com falhas de download."""
    # Cria um Makefile com uma URL inválida
    makefile_content = MAKEFILE_CONTENT.replace(
        "MODEL_URL = https://huggingface.co/",
        "MODEL_URL = https://invalid-url/"
    )
    makefile_path = test_env / "Makefile"
    makefile_path.write_text(makefile_content)
    
    # Executa o comando
    result = os.system("make download-model")
    captured = capfd.readouterr()
    
    # Verifica se o comando falhou como esperado
    assert result != 0, "O comando deveria falhar com URL inválida"
    assert "🔄 Iniciando download..." in captured.out
    assert "❌ Falha no download do modelo" in captured.out
    assert "✅ Download concluído" not in captured.out
    
    # Verifica se o arquivo não foi criado
    model_file = test_env / "models" / "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
    assert not model_file.exists(), "O arquivo do modelo não deveria existir após falha no download"

@pytest.mark.e2e
def test_model_download_during_install(test_env, capfd):
    """Testa se o modelo é baixado durante o comando make install."""
    # Remove o diretório models se existir
    models_dir = test_env / "models"
    if models_dir.exists():
        shutil.rmtree(models_dir)
    
    # Executa o comando make install
    result = os.system("make install")
    captured = capfd.readouterr()
    
    # Verifica se o comando foi executado com sucesso
    assert result == 0, "O comando install falhou"
    
    # Verifica se o modelo foi baixado
    model_file = models_dir / "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
    assert model_file.exists(), "Modelo não foi baixado durante instalação"
    
    # Verifica as mensagens de log
    assert "📥 Baixando modelo TinyLLaMA..." in captured.out
    assert "✅ Download concluído" in captured.out or "✅ Modelo já existe" in captured.out 

# Testes do ModelManager
def test_tinyllama_provider_config():
    """Testa a configuração do provedor TinyLLaMA."""
    with patch("src.core.models.load_config") as mock_config, \
         patch("llama_cpp.Llama") as mock_llama:
        
        mock_config.return_value = {
            "providers": {
                "tinyllama": {
                    "model_path": "models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
                    "n_ctx": 2048,
                    "n_threads": 4,
                    "prefix_patterns": ["tinyllama-"],
                    "default_model": "tinyllama-1.1b",
                    "models": ["tinyllama-1.1b"]
                }
            },
            "defaults": {
                "model": "tinyllama-1.1b",
                "elevation_model": "tinyllama-1.1b",
                "temperature": 0.7,
                "max_tokens": None,
                "max_retries": 3,
                "timeout": 120
            },
            "env_vars": {
                "openai_key": "OPENAI_API_KEY",
                "openrouter_key": "OPENROUTER_API_KEY",
                "gemini_key": "GEMINI_API_KEY",
                "anthropic_key": "ANTHROPIC_API_KEY",
                "default_model": "DEFAULT_MODEL",
                "elevation_model": "ELEVATION_MODEL",
                "max_retries": "MAX_RETRIES",
                "model_timeout": "MODEL_TIMEOUT",
                "fallback_enabled": "FALLBACK_ENABLED",
                "cache_enabled": "CACHE_ENABLED",
                "cache_ttl": "CACHE_TTL",
                "cache_dir": "CACHE_DIR"
            },
            "cache": {
                "enabled": False,
                "ttl": 3600,
                "directory": "/tmp/cache"
            },
            "fallback": {
                "enabled": True
            }
        }
        
        # Mock do Llama
        mock_llama.return_value = MagicMock()
        
        # Cria instância e testa
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test'}):
            manager = ModelManager("tinyllama-1.1b")
            provider = manager._get_provider("tinyllama-1.1b")
            assert provider == "tinyllama"

def test_tinyllama_generate_response():
    """Testa a geração de resposta com TinyLLaMA."""
    with patch("src.core.models.load_config") as mock_config, \
         patch("llama_cpp.Llama") as mock_llama:
        
        mock_config.return_value = {
            "providers": {
                "tinyllama": {
                    "model_path": "models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
                    "n_ctx": 2048,
                    "n_threads": 4,
                    "prefix_patterns": ["tinyllama-"],
                    "default_model": "tinyllama-1.1b",
                    "models": ["tinyllama-1.1b"]
                }
            },
            "defaults": {
                "model": "tinyllama-1.1b",
                "elevation_model": "tinyllama-1.1b",
                "temperature": 0.7,
                "max_tokens": None,
                "max_retries": 3,
                "timeout": 120
            },
            "env_vars": {
                "openai_key": "OPENAI_API_KEY",
                "openrouter_key": "OPENROUTER_API_KEY",
                "gemini_key": "GEMINI_API_KEY",
                "anthropic_key": "ANTHROPIC_API_KEY",
                "default_model": "DEFAULT_MODEL",
                "elevation_model": "ELEVATION_MODEL",
                "max_retries": "MAX_RETRIES",
                "model_timeout": "MODEL_TIMEOUT",
                "fallback_enabled": "FALLBACK_ENABLED",
                "cache_enabled": "CACHE_ENABLED",
                "cache_ttl": "CACHE_TTL",
                "cache_dir": "CACHE_DIR"
            },
            "cache": {
                "enabled": False,
                "ttl": 3600,
                "directory": "/tmp/cache"
            },
            "fallback": {
                "enabled": True
            }
        }
        
        # Mock do Llama
        mock_instance = MagicMock()
        mock_instance.create_chat_completion.return_value = {
            "choices": [{"message": {"content": "Resposta de teste"}}]
        }
        mock_llama.return_value = mock_instance
        
        # Cria instância e testa
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test'}):
            manager = ModelManager("tinyllama-1.1b")
            response = manager.generate_response(
                system_prompt="Sistema de teste",
                user_prompt="Prompt de teste"
            )
            
            # Verifica chamadas
            mock_instance.create_chat_completion.assert_called_once()
            assert response == "Resposta de teste"

def test_tinyllama_fallback():
    """Testa o fallback para TinyLLaMA."""
    with patch("src.core.models.load_config") as mock_config, \
         patch("llama_cpp.Llama") as mock_llama:
        
        mock_config.return_value = {
            "providers": {
                "tinyllama": {
                    "model_path": "models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
                    "n_ctx": 2048,
                    "n_threads": 4,
                    "prefix_patterns": ["tinyllama-"],
                    "default_model": "tinyllama-1.1b",
                    "models": ["tinyllama-1.1b"]
                }
            },
            "defaults": {
                "model": "tinyllama-1.1b",
                "elevation_model": "tinyllama-1.1b",
                "temperature": 0.7,
                "max_tokens": None,
                "max_retries": 3,
                "timeout": 120
            },
            "env_vars": {
                "openai_key": "OPENAI_API_KEY",
                "openrouter_key": "OPENROUTER_API_KEY",
                "gemini_key": "GEMINI_API_KEY",
                "anthropic_key": "ANTHROPIC_API_KEY",
                "default_model": "DEFAULT_MODEL",
                "elevation_model": "ELEVATION_MODEL",
                "max_retries": "MAX_RETRIES",
                "model_timeout": "MODEL_TIMEOUT",
                "fallback_enabled": "FALLBACK_ENABLED",
                "cache_enabled": "CACHE_ENABLED",
                "cache_ttl": "CACHE_TTL",
                "cache_dir": "CACHE_DIR"
            },
            "cache": {
                "enabled": False,
                "ttl": 3600,
                "directory": "/tmp/cache"
            },
            "fallback": {
                "enabled": True
            }
        }
        
        # Mock do Llama
        mock_instance = MagicMock()
        mock_instance.create_chat_completion.side_effect = [
            Exception("Erro de teste"),
            {"choices": [{"message": {"content": "Resposta de fallback"}}]}
        ]
        mock_llama.return_value = mock_instance
        
        # Cria instância e testa
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test'}):
            manager = ModelManager("tinyllama-1.1b")
            response = manager.generate_response(
                system_prompt="Sistema de teste",
                user_prompt="Prompt de teste"
            )
            
            # Verifica chamadas
            assert mock_instance.create_chat_completion.call_count == 2
            assert response == "Resposta de fallback" 