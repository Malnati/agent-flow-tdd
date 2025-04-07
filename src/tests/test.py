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
def mock_mkdocs():
    """Mock para o mkdocs."""
    with patch("mkdocs.commands.serve") as mock_serve, \
         patch("mkdocs.commands.build") as mock_build, \
         patch("mkdocs.commands.gh_deploy") as mock_deploy:
        mock = MagicMock()
        mock.serve = mock_serve
        mock.build = mock_build
        mock.gh_deploy = mock_deploy
        yield mock

@pytest.fixture
def mock_docs_generator():
    """Mock para o DocsGenerator."""
    with patch("src.scripts.generate_docs.DocsGenerator") as mock:
        mock_instance = MagicMock()
        mock_instance.generate_all = Mock()
        mock.return_value = mock_instance
        yield mock_instance

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

def test_status_command_success(mock_validate_env, capsys, mock_env):
    """Testa o comando status com sucesso."""
    # Execução do comando
    with pytest.raises(SystemExit) as exc_info:
        app(["status"])
        
    # Verificações
    assert exc_info.value.code == 0
    
    # Verifica saída
    captured = capsys.readouterr()
    assert "Status do Ambiente" in captured.out
    assert "✅ Ambiente configurado corretamente!" in captured.out

def test_status_command_error(mock_validate_env, capsys):
    """Testa o comando status com erro."""
    # Remove variáveis de ambiente
    with patch.dict(os.environ, {}, clear=True):
        # Execução do comando
        with pytest.raises(SystemExit) as exc_info:
            app(["status"])
            
        # Verificações
        assert exc_info.value.code == 1
        
        # Verifica saída
        captured = capsys.readouterr()
        assert "Status do Ambiente" in captured.out
        assert "❌ Algumas variáveis não estão configuradas!" in captured.out

# Testes do Banco de Dados
def test_db_init(mock_db_manager):
    """Testa inicialização do banco de dados."""
    assert mock_db_manager.db_path == ":memory:"
    assert mock_db_manager.conn is not None
    
    # Verifica se tabelas foram criadas
    cursor = mock_db_manager.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    
    expected_tables = {
        "runs",
        "run_items", 
        "guardrail_results",
        "raw_responses",
        "model_cache"
    }
    
    assert tables.issuperset(expected_tables)

def test_db_log_run(mock_db_manager):
    """Testa registro de execução."""
    run_id = mock_db_manager.log_run(
        session_id="test-session",
        input="test input",
        final_output={"result": "test"},
        last_agent="test-agent",
        output_type="json"
    )
    
    assert run_id is not None
    
    # Verifica registro na tabela runs
    cursor = mock_db_manager.conn.cursor()
    cursor.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
    run = cursor.fetchone()
    
    assert run["session_id"] == "test-session"
    assert run["prompt"] == "test input"
    assert run["format"] == "json"
    
    # Verifica item de execução
    cursor.execute("SELECT * FROM run_items WHERE run_id = ?", (run_id,))
    item = cursor.fetchone()
    
    assert item["type"] == "input"
    assert item["content"] == "test input"
    
    # Verifica resultado de guardrail
    cursor.execute("SELECT * FROM guardrail_results WHERE run_id = ?", (run_id,))
    result = cursor.fetchone()
    
    assert result["type"] == "input"
    assert result["passed"] == True
    
    # Verifica resposta bruta
    cursor.execute("SELECT * FROM raw_responses WHERE run_id = ?", (run_id,))
    response = cursor.fetchone()
    
    assert response["response_id"] == "input"
    assert json.loads(response["content"]) == {"result": "test"}

def test_db_log_run_item(mock_db_manager):
    """Testa registro de item de execução."""
    run_id = mock_db_manager.log_run(
        session_id="test-session",
        input="test input",
        final_output=None,
        last_agent=None,
        output_type="json"
    )
    
    mock_db_manager.log_run_item(
        run_id=run_id,
        item_type="test",
        raw_item={"test": "data"},
        source_agent="source",
        target_agent="target"
    )
    
    cursor = mock_db_manager.conn.cursor()
    cursor.execute("SELECT * FROM run_items WHERE run_id = ? AND type = ?", 
                  (run_id, "test"))
    item = cursor.fetchone()
    
    assert item is not None
    assert json.loads(item["content"]) == {"test": "data"}

def test_db_log_guardrail(mock_db_manager):
    """Testa registro de resultado de guardrail."""
    run_id = mock_db_manager.log_run(
        session_id="test-session",
        input="test input", 
        final_output=None,
        last_agent=None,
        output_type="json"
    )
    
    mock_db_manager.log_guardrail_result(
        run_id=run_id,
        guardrail_type="test",
        results={
            "passed": True,
            "results": {"test": "data"}
        }
    )
    
    cursor = mock_db_manager.conn.cursor()
    
    # Verifica resultado
    cursor.execute("SELECT * FROM guardrail_results WHERE run_id = ? AND type = ?",
                  (run_id, "test"))
    result = cursor.fetchone()
    
    assert result is not None
    assert result["passed"] == True
    
    # Verifica resposta bruta
    cursor.execute("SELECT * FROM raw_responses WHERE run_id = ? AND response_id = ?",
                  (run_id, "test"))
    response = cursor.fetchone()
    
    assert response is not None
    assert json.loads(response["content"]) == {"test": "data"}

def test_db_log_raw_response(mock_db_manager):
    """Testa registro de resposta bruta."""
    run_id = mock_db_manager.log_run(
        session_id="test-session",
        input="test input",
        final_output=None,
        last_agent=None,
        output_type="json"
    )
    
    mock_db_manager.log_raw_response(
        run_id=run_id,
        response={"test": "data"}
    )
    
    cursor = mock_db_manager.conn.cursor()
    cursor.execute("SELECT * FROM raw_responses WHERE run_id = ? AND response_id = ?",
                  (run_id, "output"))
    response = cursor.fetchone()
    
    assert response is not None
    assert json.loads(response["content"]) == {"test": "data"}

def test_db_get_runs(mock_db_manager):
    """Testa listagem de execuções."""
    # Registra algumas execuções
    for i in range(3):
        mock_db_manager.log_run(
            session_id=f"session-{i}",
            input=f"input {i}",
            final_output={"result": f"test {i}"},
            last_agent=None,
            output_type="json"
        )
    
    # Lista todas execuções
    runs = mock_db_manager.get_runs()
    assert len(runs) == 3
    
    # Verifica ordenação (mais recente primeiro)
    assert runs[0]["session_id"] == "session-2"
    assert runs[1]["session_id"] == "session-1"
    assert runs[2]["session_id"] == "session-0"
    
    # Testa limite
    runs = mock_db_manager.get_runs(limit=2)
    assert len(runs) == 2
    assert runs[0]["session_id"] == "session-2"
    assert runs[1]["session_id"] == "session-1"

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

@pytest.mark.usefixtures("mock_env")
def test_docs_serve_command(mock_mkdocs, capfd):
    """Testa o comando docs-serve."""
    # Simula execução do comando
    os.system("make docs-serve")
    
    # Verifica mensagens no console
    captured = capfd.readouterr()
    assert "📚 Iniciando servidor de documentação..." in captured.out

@pytest.mark.usefixtures("mock_env")
def test_docs_build_command(mock_mkdocs, capfd):
    """Testa o comando docs-build."""
    # Simula execução do comando
    os.system("make docs-build")
    
    # Verifica mensagens no console
    captured = capfd.readouterr()
    assert "📚 Gerando documentação estática..." in captured.out

@pytest.mark.usefixtures("mock_env")
def test_docs_deploy_command(mock_mkdocs, capfd):
    """Testa o comando docs-deploy."""
    # Simula execução do comando
    os.system("make docs-deploy")
    
    # Verifica mensagens no console
    captured = capfd.readouterr()
    assert "📚 Publicando documentação no GitHub Pages..." in captured.out

@pytest.mark.usefixtures("mock_env")
def test_docs_generate_command(mock_docs_generator, capfd):
    """Testa o comando docs-generate."""
    # Simula execução do comando
    os.system("make docs-generate")
    
    # Verifica mensagens no console
    captured = capfd.readouterr()
    assert "🤖 Gerando documentação via IA..." in captured.out
    assert "✅ Documentação gerada com sucesso!" in captured.out

@pytest.mark.usefixtures("mock_env")
def test_docs_generate_error_handling(mock_docs_generator, capfd):
    """Testa o tratamento de erros no comando docs-generate."""
    # Configura o mock para lançar uma exceção
    error_msg = "Erro ao gerar documentação"
    mock_docs_generator.generate_docs.side_effect = Exception(error_msg)
    
    # Simula execução do comando
    os.system("make docs-generate")
    
    # Verifica mensagens de erro no console
    captured = capfd.readouterr()
    assert error_msg in captured.err

def test_docs_generator_section_creation(mock_model_manager, mock_db_manager, tmp_path):
    """Testa a criação de seções pelo DocsGenerator."""
    from src.scripts.generate_docs import DocsGenerator

    # Configura o mock do modelo para retornar um JSON válido
    mock_model_manager.generate_response.return_value = json.dumps({
        "name": "Documentação",
        "description": "Documentação do sistema",
        "objectives": ["Documentar o sistema"],
        "requirements": ["Markdown"],
        "constraints": ["Tempo"]
    })

    # Inicializa o gerador com o diretório temporário
    generator = DocsGenerator(
        model_manager=mock_model_manager,
        db_manager=mock_db_manager,
        docs_dir=tmp_path
    )

    # Usa dados de teste da configuração
    test_section = TEST_CONFIG["docs"]["test_data"]["mock_section"]
    generator.generate_section(test_section["section"], test_section["subsection"])

    # Verifica se o diretório e arquivo foram criados
    section_dir = tmp_path / test_section["section"]
    assert section_dir.exists()
    assert (section_dir / f"{test_section['subsection']}.md").exists()

def test_docs_generator_orchestrator_integration(mock_model_manager, mock_db_manager, tmp_path):
    """Testa a integração do DocsGenerator com o AgentOrchestrator."""
    from src.scripts.generate_docs import DocsGenerator

    # Configura o mock do modelo para retornar um JSON válido
    mock_model_manager.generate_response.return_value = json.dumps({
        "name": "Documentação",
        "description": "Documentação do sistema",
        "objectives": ["Documentar o sistema"],
        "requirements": ["Markdown"],
        "constraints": ["Tempo"]
    })

    # Inicializa o gerador com o diretório temporário
    generator = DocsGenerator(
        model_manager=mock_model_manager,
        db_manager=mock_db_manager,
        docs_dir=tmp_path
    )

    # Gera uma seção
    generator.generate_section("test")

    # Verifica se o arquivo foi criado com o conteúdo correto
    output_file = tmp_path / "test" / "index.md"
    assert output_file.exists()
    assert output_file.read_text() == mock_model_manager.generate_response.return_value

def test_docs_generate_error_handling(mock_model_manager, mock_db_manager, tmp_path, capsys):
    """Testa o tratamento de erros no comando docs-generate."""
    from src.scripts.generate_docs import DocsGenerator

    # Configura o mock para retornar um JSON inválido
    mock_model_manager.generate_response.return_value = "resposta inválida"

    # Inicializa o gerador com o diretório temporário
    generator = DocsGenerator(
        model_manager=mock_model_manager,
        db_manager=mock_db_manager,
        docs_dir=tmp_path
    )

    # Tenta gerar uma seção
    with pytest.raises(ValueError) as exc_info:
        generator.generate_section("test")

    # Verifica se a mensagem de erro contém a informação sobre campos ausentes
    assert "Campos obrigatórios ausentes" in str(exc_info.value)

    # Verifica mensagens de erro no console
    captured = capsys.readouterr()
    assert "Erro ao gerar seção test" in captured.err

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

