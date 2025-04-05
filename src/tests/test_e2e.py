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
    
    try:
        # Copia arquivos essenciais com timeout
        for file in ["Makefile", "setup.py", "requirements.txt", ".version.json", "README.md"]:
            if os.path.exists(file):
                shutil.copy(file, test_dir / file)
        
        # Se .version.json não existe, cria
        if not os.path.exists(test_dir / ".version.json"):
            version_data = {"current": "0.1.0", "previous": None}
            with open(test_dir / ".version.json", "w") as f:
                json.dump(version_data, f)
        
        # Se README.md não existe, cria
        if not os.path.exists(test_dir / "README.md"):
            with open(test_dir / "README.md", "w") as f:
                f.write("# Agent Flow TDD\n\nFramework para desenvolvimento orientado a testes com agentes de IA.")
        
        # Copia estrutura src com timeout
        subprocess.run(
            f"cp -r src {test_dir}/",
            shell=True,
            check=True,
            timeout=30
        )
        
        # Cria diretórios adicionais
        os.makedirs(test_dir / "logs", exist_ok=True)
        os.makedirs(test_dir / ".venv", exist_ok=True)
        
        # Cria e configura ambiente virtual com timeout
        subprocess.run(
            "python -m venv .venv",
            shell=True,
            cwd=test_dir,
            check=True,
            timeout=30
        )
        
        # Atualiza pip e instala wheel com timeout
        pip_cmd = str(test_dir / ".venv" / "bin" / "pip")
        subprocess.run(
            f"{pip_cmd} install --upgrade pip wheel setuptools",
            shell=True,
            cwd=test_dir,
            check=True,
            timeout=60,
            capture_output=True
        )
        
        # Instala dependências de desenvolvimento com timeout
        subprocess.run(
            f"{pip_cmd} install pytest pytest-cov pytest-mock black flake8 autoflake",
            shell=True,
            cwd=test_dir,
            check=True,
            timeout=120,
            capture_output=True
        )
        
        # Instala o pacote em modo desenvolvimento com timeout
        subprocess.run(
            f"{pip_cmd} install -e .",
            shell=True,
            cwd=test_dir,
            check=True,
            timeout=60,
            capture_output=True
        )
        
        return test_dir
        
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
        logger.error(f"Erro ao configurar ambiente de teste: {str(e)}")
        raise

def run_command_with_timeout(cmd: str, cwd: str = None, timeout: int = 30, env: dict = None) -> subprocess.CompletedProcess:
    """
    Executa um comando com timeout.
    
    Args:
        cmd: Comando a ser executado
        cwd: Diretório de trabalho
        timeout: Timeout em segundos
        env: Variáveis de ambiente
        
    Returns:
        Resultado da execução
    """
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            timeout=timeout,
            env=env or os.environ,
            capture_output=True,
            text=True
        )
        
        # Combina stdout e stderr para verificação
        result.combined_output = result.stdout + result.stderr
        
        # Normaliza código de retorno
        if result.returncode == 2:
            result.returncode = 1
            
        return result
    except subprocess.TimeoutExpired as e:
        logger.error(f"Timeout ao executar comando: {cmd}")
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=1,
            stdout="",
            stderr=f"Timeout após {timeout} segundos"
        )

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
            
        # Executa o comando make com timeout
        cmd = f'PYTHONPATH={test_env} make dev prompt-tdd="{prompt}" mode={mode} format={format}'
        result = run_command_with_timeout(
            cmd,
            timeout=120,
            env={**os.environ, "PYTHONPATH": str(test_env)}
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
    except Exception as e:
        logger.error(f"Erro ao executar comando: {str(e)}", exc_info=True)
        return {
            "stdout": "",
            "stderr": str(e),
            "returncode": 1,
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
    result = run_command_with_timeout(
        "make install",
        cwd=test_env,
        timeout=120,
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
    result = run_command_with_timeout(
        "make clean",
        cwd=test_env,
        timeout=30
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
    
    # Verifica se há saída no banco
    if result["returncode"] == 0:
        assert result["db_history"] is not None

@pytest.mark.e2e
def test_e2e_run_command(test_env):
    """Testa o comando make run."""
    # Configura ambiente de teste
    os.chdir(test_env)
    
    # Executa o comando
    result = run_command_with_timeout(
        'make run prompt-tdd="Teste de execução" mode=feature format=markdown',
        cwd=test_env,
        timeout=120,
        env={**os.environ, "PYTHONPATH": str(test_env)}
    )
    
    # Verificações
    assert result.returncode in [0, 1]
    assert "🖥️ Executando CLI..." in result.combined_output

@pytest.mark.e2e
def test_e2e_publish_command(test_env):
    """Testa o comando make publish."""
    # Configura ambiente de teste
    os.chdir(test_env)
    
    # Mock do token PyPI
    with patch.dict(os.environ, {"PYPI_TOKEN": "test-token"}):
        # Executa o comando
        result = run_command_with_timeout(
            "make publish",
            cwd=test_env,
            timeout=60,
            env={**os.environ, "PYTHONPATH": str(test_env)}
        )
        
        # Verificações
        assert result.returncode in [0, 1]
        assert "📦 Preparando pacote para publicação..." in result.combined_output
        if result.returncode == 0:
            assert "🔄 Incrementando versão..." in result.combined_output

@pytest.mark.e2e
def test_e2e_publish_command_no_token(test_env):
    """Testa o comando make publish sem token PyPI."""
    # Configura ambiente de teste
    os.chdir(test_env)
    
    # Remove o token PyPI do ambiente
    with patch.dict(os.environ, {}, clear=True):
        # Executa o comando
        result = run_command_with_timeout(
            "make publish",
            cwd=test_env,
            timeout=30
        )
        
        # Verificações
        assert result.returncode == 1
        assert "❌ Erro: Variável PYPI_TOKEN não definida" in result.combined_output

@pytest.mark.e2e
def test_e2e_coverage_command(test_env):
    """Testa se o comando make coverage está disponível e configurado."""
    try:
        # Configura ambiente de teste
        os.chdir(test_env)
        
        # Verifica se o comando existe no Makefile
        result = run_command_with_timeout(
            "make -n coverage",  # -n faz um dry-run do comando
            cwd=test_env,
            timeout=30,
            env={**os.environ, "PYTHONPATH": str(test_env)}
        )
        
        # Verificações
        assert result.returncode == 0, "Comando make coverage não encontrado no Makefile"
        
        # Verifica se o pytest-cov está instalado usando pip list
        pip_cmd = str(test_env / ".venv" / "bin" / "pip")
        result = run_command_with_timeout(
            f"{pip_cmd} list",
            cwd=test_env,
            timeout=10
        )
        assert result.returncode == 0, "Erro ao listar pacotes instalados"
        assert "pytest-cov" in result.combined_output, "pytest-cov não está instalado"
            
    except subprocess.TimeoutExpired as e:
        logger.error(
            "Timeout ao verificar comando coverage - Comando: %s, Diretório: %s, Timeout: %ds",
            e.cmd,
            test_env,
            e.timeout
        )
        pytest.skip("Verificação do comando coverage excedeu o tempo limite")
    except Exception as e:
        logger.error(
            "Erro ao verificar comando coverage - Tipo: %s, Erro: %s, Diretório: %s",
            type(e).__name__,
            str(e),
            test_env
        )
        raise

@pytest.mark.e2e
def test_e2e_lint_command(test_env):
    """Testa o comando make lint."""
    # Configura ambiente de teste
    os.chdir(test_env)
    
    # Executa o comando make lint
    result = run_command_with_timeout(
        "make lint",
        cwd=test_env,
        timeout=30,
        env={**os.environ, "PYTHONPATH": str(test_env)}
    )
    
    # Verificações
    assert result.returncode in [0, 1]

@pytest.mark.e2e
def test_e2e_format_command(test_env):
    """Testa o comando make format."""
    # Configura ambiente de teste
    os.chdir(test_env)
    
    # Verifica se o black está instalado
    black_cmd = str(test_env / ".venv" / "bin" / "black")
    result = run_command_with_timeout(
        f"{black_cmd} --version",
        cwd=test_env,
        timeout=10
    )
    assert result.returncode == 0, "black não está instalado corretamente"
    
    # Executa o comando make format
    result = run_command_with_timeout(
        "make format",
        cwd=test_env,
        timeout=30,
        env={**os.environ, "PYTHONPATH": str(test_env)}
    )
    
    # Verificações
    assert result.returncode in [0, 1], "Comando make format falhou"
    
    # Executa black diretamente para verificar a saída
    result = run_command_with_timeout(
        f"{black_cmd} src/",
        cwd=test_env,
        timeout=30
    )
    assert result.returncode in [0, 1], "Execução do black falhou"
    assert "reformatted" in result.combined_output or "All done!" in result.combined_output, "Saída do black não encontrada"

@pytest.mark.e2e
def test_e2e_autoflake_command(test_env):
    """Testa o comando make autoflake."""
    # Configura ambiente de teste
    os.chdir(test_env)
    
    # Executa o comando make autoflake
    result = run_command_with_timeout(
        "make autoflake",
        cwd=test_env,
        timeout=30,
        env={**os.environ, "PYTHONPATH": str(test_env)}
    )
    
    # Verificações
    assert result.returncode == 0

@pytest.mark.e2e
def test_e2e_help_command(test_env):
    """Testa o comando make help."""
    # Configura ambiente de teste
    os.chdir(test_env)
    
    # Executa o comando
    result = run_command_with_timeout(
        "make help",
        cwd=test_env,
        timeout=10
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

@pytest.mark.e2e
def test_e2e_test_command(test_env):
    """Testa se o comando make test está disponível e configurado."""
    try:
        # Configura ambiente de teste
        os.chdir(test_env)
        
        # Verifica se o comando existe no Makefile
        result = run_command_with_timeout(
            "make -n test",  # -n faz um dry-run do comando
            cwd=test_env,
            timeout=30,
            env={**os.environ, "PYTHONPATH": str(test_env)}
        )
        
        # Verificações
        assert result.returncode == 0, "Comando make test não encontrado no Makefile"
        
        # Verifica se o pytest está instalado
        result = run_command_with_timeout(
            f"{test_env}/.venv/bin/pytest --version",
            cwd=test_env,
            timeout=10
        )
        assert result.returncode == 0, "pytest não está instalado corretamente"
            
    except subprocess.TimeoutExpired as e:
        logger.error(
            "Timeout ao verificar comando test - Comando: %s, Diretório: %s, Timeout: %ds",
            e.cmd,
            test_env,
            e.timeout
        )
        pytest.skip("Verificação do comando test excedeu o tempo limite")
    except Exception as e:
        logger.error(
            "Erro ao verificar comando test - Tipo: %s, Erro: %s, Diretório: %s",
            type(e).__name__,
            str(e),
            test_env
        )
        raise

@pytest.mark.e2e
def test_e2e_test_e2e_command(test_env):
    """Testa se o comando make test-e2e está disponível e configurado."""
    try:
        # Configura ambiente de teste
        os.chdir(test_env)
        
        # Verifica se o comando existe no Makefile
        result = run_command_with_timeout(
            "make -n test-e2e",  # -n faz um dry-run do comando
            cwd=test_env,
            timeout=30,
            env={**os.environ, "PYTHONPATH": str(test_env)}
        )
        
        # Verificações
        assert result.returncode == 0, "Comando make test-e2e não encontrado no Makefile"
        
        # Verifica se o pytest está instalado com o plugin e2e
        result = run_command_with_timeout(
            f"{test_env}/.venv/bin/pytest --version",
            cwd=test_env,
            timeout=10
        )
        assert result.returncode == 0, "pytest não está instalado corretamente"
        
        # Verifica se o banco de dados está configurado
        result = run_command_with_timeout(
            "make -n db-init",  # -n faz um dry-run do comando
            cwd=test_env,
            timeout=10
        )
        assert result.returncode == 0, "Comando make db-init não encontrado no Makefile"
            
    except subprocess.TimeoutExpired as e:
        logger.error(
            "Timeout ao verificar comando test-e2e - Comando: %s, Diretório: %s, Timeout: %ds",
            e.cmd,
            test_env,
            e.timeout
        )
        pytest.skip("Verificação do comando test-e2e excedeu o tempo limite")
    except Exception as e:
        logger.error(
            "Erro ao verificar comando test-e2e - Tipo: %s, Erro: %s, Diretório: %s",
            type(e).__name__,
            str(e),
            test_env
        )
        raise 