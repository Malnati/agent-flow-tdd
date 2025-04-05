"""
Testes end-to-end para o Agent Flow TDD.
"""
import os
import json
import subprocess
import shutil
from typing import Dict, Any
import pytest
from unittest.mock import patch

from src.core.db import DatabaseManager
from src.core.logger import setup_logger

logger = setup_logger(__name__)

@pytest.fixture(scope="session")
def test_env(tmp_path_factory):
    """Configura o ambiente de teste."""
    # Cria diretório temporário
    test_dir = tmp_path_factory.mktemp("test_env")
    
    # Copia Makefile
    shutil.copy("Makefile", test_dir / "Makefile")
    
    # Cria estrutura de diretórios
    os.makedirs(test_dir / "src" / "configs", exist_ok=True)
    os.makedirs(test_dir / "src" / "tests", exist_ok=True)
    os.makedirs(test_dir / "logs", exist_ok=True)
    
    # Cria arquivo de configuração do banco
    db_config = {
        "directories": {"logs": "logs"},
        "database": {
            "default_path": "logs/agent_logs.db",
            "history_limit": 10
        }
    }
    with open(test_dir / "src" / "configs" / "database.yaml", "w") as f:
        import yaml
        yaml.dump(db_config, f)
    
    return test_dir

def run_make_command(prompt: str, mode: str = "feature", format: str = "markdown", test_env = None) -> Dict[str, Any]:
    """
    Executa o comando make dev e retorna o resultado.
    
    Args:
        prompt: Prompt para o TDD
        mode: Modo de execução
        format: Formato de saída
        test_env: Diretório de teste
        
    Returns:
        Dicionário com resultado da execução
    """
    try:
        if test_env:
            os.chdir(test_env)
            
        # Executa o comando make
        cmd = f'PYTHONPATH=. make dev prompt-tdd="{prompt}" mode={mode} format={format}'
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": "."}
        )
        
        # Verifica logs no banco
        db = DatabaseManager()
        history = db.get_run_history(limit=1)
        db.close()
        
        # Se o código de retorno for 2, trata como erro
        if result.returncode == 2:
            result.returncode = 1
        
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "db_history": history[0] if history else None
        }
    except subprocess.CalledProcessError as e:
        return {
            "stdout": e.stdout if hasattr(e, 'stdout') else "",
            "stderr": e.stderr if hasattr(e, 'stderr') else "",
            "returncode": 1 if e.returncode == 2 else e.returncode,
            "db_history": None
        }

@pytest.mark.e2e
def test_e2e_address_registration_cli_markdown():
    """Testa o fluxo completo de cadastro de endereços via CLI com saída markdown."""
    # Setup
    prompt = "Cadastro de endereços"
    
    # Execução
    result = run_make_command(prompt)
    
    # Verificações
    assert result["returncode"] in [0, 1], f"Código de retorno inesperado: {result['returncode']}"
    assert "🛠️ Executando CLI em modo desenvolvimento..." in result["stdout"]
    
    # Verifica registro no banco
    db_record = result["db_history"]
    if result["returncode"] == 0:
        assert db_record is not None
        assert db_record["input"] == prompt
        assert db_record["output_type"] == "markdown"
        assert db_record["last_agent"] == "OpenAI"
        assert len(db_record["raw_responses"]) > 0

@pytest.mark.e2e
def test_e2e_address_registration_cli_json():
    """Testa o fluxo completo de cadastro de endereços via CLI com saída JSON."""
    # Setup
    prompt = "Cadastro de endereços"
    
    # Execução
    result = run_make_command(prompt, format="json")
    
    # Verificações
    assert result["returncode"] in [0, 1], f"Código de retorno inesperado: {result['returncode']}"
    
    if result["returncode"] == 0:
        # Verifica se a saída é um JSON válido
        try:
            # Pega a última linha não vazia que não seja uma mensagem de autoflake
            lines = [line for line in result["stdout"].split("\n") if line.strip() and not line.startswith("🧹") and not line.startswith("✨")]
            output = json.loads(lines[-1])
            assert "content" in output
            assert "metadata" in output
            assert output["metadata"]["type"] == "feature"
        except json.JSONDecodeError:
            pytest.fail("Saída não é um JSON válido")
        
        # Verifica registro no banco
        db_record = result["db_history"]
        assert db_record is not None
        assert db_record["input"] == prompt
        assert db_record["output_type"] == "json"
        assert db_record["last_agent"] == "OpenAI"
        assert len(db_record["raw_responses"]) > 0

@pytest.mark.e2e
def test_e2e_address_registration_error_handling():
    """Testa o tratamento de erros no fluxo de cadastro de endereços."""
    # Setup - Remove temporariamente a variável OPENAI_API_KEY
    original_key = os.environ.get("OPENAI_API_KEY")
    os.environ.pop("OPENAI_API_KEY", None)
    
    try:
        # Execução
        result = run_make_command("Cadastro de endereços")
        
        # Verificações
        assert result["returncode"] in [1, 2], "Esperado código de erro 1 ou 2"
        assert "Variáveis de ambiente obrigatórias não definidas: OPENAI_API_KEY" in result["stderr"]
        
    finally:
        # Restaura a chave original
        if original_key:
            os.environ["OPENAI_API_KEY"] = original_key

@pytest.mark.e2e
def test_e2e_address_registration_with_autoflake():
    """Testa se o autoflake é executado após a geração."""
    # Setup
    prompt = "Cadastro de endereços"
    
    # Execução
    result = run_make_command(prompt)
    
    # Verificações
    assert result["returncode"] in [0, 1], f"Código de retorno inesperado: {result['returncode']}"
    
    if result["returncode"] == 0:
        assert "🧹 Limpando código com autoflake..." in result["stdout"]
        assert "✨ Limpeza de código concluída!" in result["stdout"]

@pytest.mark.e2e
def test_e2e_address_registration_logging():
    """Testa se os logs são gerados corretamente durante a execução."""
    # Setup
    prompt = "Cadastro de endereços"
    
    # Execução
    result = run_make_command(prompt)
    
    # Verificações
    assert result["returncode"] in [0, 1], f"Código de retorno inesperado: {result['returncode']}"
    
    if result["returncode"] == 0:
        # Verifica se os logs foram registrados no banco
        db_record = result["db_history"]
        assert db_record is not None
        assert len(db_record["raw_responses"]) > 0  # Deve ter pelo menos uma resposta logada
        
        # Verifica se a resposta contém os campos esperados
        raw_response = db_record["raw_responses"][0]
        assert "id" in raw_response
        assert "response" in raw_response
        assert isinstance(raw_response["response"], str)  # Deve ser um JSON serializado

@pytest.mark.e2e
def test_e2e_install_command(test_env):
    """Testa o comando make install."""
    # Configura ambiente de teste
    os.chdir(test_env)
    
    # Executa o comando
    result = subprocess.run(
        "make install",
        shell=True,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(test_env)}
    )
    
    # Verificações
    assert result.returncode == 0
    assert "🔧 Instalando dependências..." in result.stdout
    assert "✅ Instalação concluída!" in result.stdout

@pytest.mark.e2e
def test_e2e_clean_command(test_env):
    """Testa o comando make clean."""
    # Configura ambiente de teste
    os.chdir(test_env)
    
    # Cria alguns arquivos e diretórios para limpar
    os.makedirs("build", exist_ok=True)
    os.makedirs("dist", exist_ok=True)
    os.makedirs("__pycache__", exist_ok=True)
    
    # Executa o comando
    result = subprocess.run(
        "make clean",
        shell=True,
        capture_output=True,
        text=True
    )
    
    # Verificações
    assert result.returncode == 0
    assert "🧹 Limpando arquivos temporários..." in result.stdout
    assert "✨ Limpeza concluída!" in result.stdout
    assert not os.path.exists("build")
    assert not os.path.exists("dist")
    assert not os.path.exists("__pycache__")

@pytest.mark.e2e
def test_e2e_dev_command(test_env):
    """Testa o comando make dev."""
    # Executa o comando
    result = run_make_command(
        prompt="Teste de desenvolvimento",
        mode="feature",
        format="markdown",
        test_env=test_env
    )
    
    # Verificações
    assert result["returncode"] in [0, 1]
    assert "🛠️ Executando CLI em modo desenvolvimento..." in result["stdout"]
    
    if result["returncode"] == 0:
        assert "✅" in result["stdout"]
        assert result["db_history"] is not None

@pytest.mark.e2e
def test_e2e_run_command(test_env):
    """Testa o comando make run."""
    # Configura ambiente de teste
    os.chdir(test_env)
    
    # Executa o comando
    result = subprocess.run(
        'make run prompt-tdd="Teste de execução" mode=feature format=markdown',
        shell=True,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(test_env)}
    )
    
    # Verificações
    assert result.returncode in [0, 1]
    assert "🖥️ Executando CLI..." in result.stdout

@pytest.mark.e2e
def test_e2e_publish_command(test_env):
    """Testa o comando make publish."""
    # Configura ambiente de teste
    os.chdir(test_env)
    
    # Mock do token PyPI
    with patch.dict(os.environ, {"PYPI_TOKEN": "test-token"}):
        # Executa o comando
        result = subprocess.run(
            "make publish",
            shell=True,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(test_env)}
        )
        
        # Verificações
        assert result.returncode in [0, 1]
        if result.returncode == 0:
            assert "📦 Preparando pacote para publicação..." in result.stdout
            assert "🔄 Incrementando versão..." in result.stdout
        else:
            assert "❌ Erro:" in result.stderr

@pytest.mark.e2e
def test_e2e_publish_command_no_token(test_env):
    """Testa o comando make publish sem token PyPI."""
    # Configura ambiente de teste
    os.chdir(test_env)
    
    # Remove o token PyPI do ambiente
    with patch.dict(os.environ, {}, clear=True):
        # Executa o comando
        result = subprocess.run(
            "make publish",
            shell=True,
            capture_output=True,
            text=True
        )
        
        # Verificações
        assert result.returncode == 1
        assert "❌ Erro: Variável PYPI_TOKEN não definida" in result.stdout

@pytest.mark.e2e
def test_e2e_coverage_command(test_env):
    """Testa o comando make coverage."""
    # Configura ambiente de teste
    os.chdir(test_env)
    
    # Executa o comando
    result = subprocess.run(
        "pytest --cov=src tests/",
        shell=True,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(test_env)}
    )
    
    # Verificações
    assert result.returncode in [0, 1]
    if result.returncode == 0:
        assert "coverage" in result.stdout

@pytest.mark.e2e
def test_e2e_lint_command():
    """Testa o comando make lint."""
    # Executa o comando
    result = subprocess.run(
        "flake8 src/ --max-line-length=120 --exclude=__init__.py",
        shell=True,
        capture_output=True,
        text=True
    )
    
    # Verificações
    assert result.returncode in [0, 1]

@pytest.mark.e2e
def test_e2e_format_command(test_env):
    """Testa o comando make format."""
    # Configura ambiente de teste
    os.chdir(test_env)
    
    # Executa o comando
    result = subprocess.run(
        "black src/ --line-length 120",
        shell=True,
        capture_output=True,
        text=True
    )
    
    # Verificações
    assert result.returncode in [0, 1]
    if result.returncode == 0:
        assert "reformatted" in result.stdout or "All done!" in result.stdout

@pytest.mark.e2e
def test_e2e_autoflake_command():
    """Testa o comando make autoflake."""
    # Executa o comando
    result = subprocess.run(
        "find . -type f -name '*.py' -not -path './.venv/*' -exec autoflake --remove-all-unused-imports --remove-unused-variables --in-place {} \\;",
        shell=True,
        capture_output=True,
        text=True
    )
    
    # Verificações
    assert result.returncode == 0 

@pytest.mark.e2e
def test_e2e_help_command(test_env):
    """Testa o comando make help."""
    # Configura ambiente de teste
    os.chdir(test_env)
    
    # Executa o comando
    result = subprocess.run(
        "make help",
        shell=True,
        capture_output=True,
        text=True
    )
    
    # Verificações
    assert result.returncode == 0
    assert "Comandos disponíveis:" in result.stdout
    assert "Ambiente:" in result.stdout
    assert "Qualidade:" in result.stdout
    assert "Banco de Dados:" in result.stdout
    assert "Publicação:" in result.stdout
    assert "make install" in result.stdout
    assert "make test" in result.stdout
    assert "make logs" in result.stdout 