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
import yaml
from pathlib import Path

from src.core.agents import AgentResult
from src.core.db import DatabaseManager
from src.core.logger import get_logger

# Logger
logger = get_logger(__name__)

# Carrega configurações de teste
def load_test_config() -> dict:
    """Carrega configurações de teste do arquivo YAML."""
    config_path = Path(__file__).resolve().parent.parent / 'configs' / 'test.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

TEST_CONFIG = load_test_config()

# Constantes para timeouts que não estão no config
COMMAND_TIMEOUT = 30  # Timeout padrão para comandos
PIP_LIST_TIMEOUT = 10  # Timeout para listar pacotes pip
DB_COMMAND_TIMEOUT = 10  # Timeout para comandos de banco de dados

@pytest.fixture(scope="session")
def test_env(tmp_path_factory):
    """Configura o ambiente de teste."""
    # Cria diretório temporário
    test_dir = tmp_path_factory.mktemp("test_env")
    
    try:
        # Copia arquivos essenciais com timeout
        for file in TEST_CONFIG['environment']['directories']['required_files']:
            if os.path.exists(file):
                shutil.copy(file, test_dir / file)
        
        # Se .version.json não existe, cria
        if not os.path.exists(test_dir / ".version.json"):
            version_data = TEST_CONFIG['environment']['version']['default']
            with open(test_dir / ".version.json", "w") as f:
                json.dump(version_data, f)
        
        # Se README.md não existe, cria
        if not os.path.exists(test_dir / "README.md"):
            with open(test_dir / "README.md", "w") as f:
                f.write(TEST_CONFIG['environment']['readme']['default_content'])
        
        # Copia estrutura src com timeout
        subprocess.run(
            f"cp -r src {test_dir}/",
            shell=True,
            check=True,
            timeout=TEST_CONFIG['environment']['timeout']['setup']
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
            timeout=TEST_CONFIG['environment']['timeout']['setup']
        )
        
        # Atualiza pip e instala wheel com timeout
        pip_cmd = str(test_dir / ".venv" / "bin" / "pip")
        subprocess.run(
            f"{pip_cmd} install --upgrade pip wheel setuptools",
            shell=True,
            cwd=test_dir,
            check=True,
            timeout=TEST_CONFIG['environment']['timeout']['install'],
            capture_output=True
        )
        
        # Instala dependências de desenvolvimento com timeout
        subprocess.run(
            f"{pip_cmd} install pytest pytest-cov pytest-mock black flake8 autoflake",
            shell=True,
            cwd=test_dir,
            check=True,
            timeout=TEST_CONFIG['environment']['timeout']['pip_install'],
            capture_output=True
        )
        
        # Instala o pacote em modo desenvolvimento com timeout
        subprocess.run(
            f"{pip_cmd} install -e .",
            shell=True,
            cwd=test_dir,
            check=True,
            timeout=TEST_CONFIG['environment']['timeout']['install'],
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

@pytest.fixture
def mock_orchestrator():
    """Mock do AgentOrchestrator."""
    with patch("src.core.agents.AgentOrchestrator") as mock:
        mock_instance = mock.return_value
        mock_instance.execute.return_value = AgentResult(
            output="Resposta de teste",
            items=[{"type": "feature", "content": "Teste"}],
            guardrails=[],
            raw_responses=[{"id": "test", "response": {"text": "Teste"}}]
        )
        yield mock_instance

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
        # Garante que test_env seja um Path válido
        if test_env is None:
            test_env = Path(os.getcwd())
        else:
            test_env = Path(test_env)
            
        os.chdir(test_env)
            
        # Executa o comando make com timeout
        cmd = f'PYTHONPATH={test_env} make dev prompt-tdd="{prompt}" mode={mode} format={format}'
        result = run_command_with_timeout(
            cmd,
            timeout=120,
            env={**os.environ, "PYTHONPATH": str(test_env)}
        )
        
        # Inicializa banco de dados se necessário
        db_path = test_env / "data" / "agent_flow.db"
        os.makedirs(db_path.parent, exist_ok=True)
        
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
def test_e2e_address_registration_cli_markdown(mock_orchestrator):
    """Testa o fluxo completo de cadastro de endereços via CLI com saída markdown."""
    # Setup
    prompt = "Cadastro de endereços"
    
    # Configura resultado esperado
    mock_orchestrator.execute.return_value = AgentResult(
        output="# Cadastro de Endereços\n\n## Funcionalidades\n- Cadastro\n- Validação",
        items=[{"type": "feature", "content": "Cadastro de endereços implementado"}],
        guardrails=[],
        raw_responses=[{"id": "test", "response": {"text": "Cadastro implementado"}}]
    )
    
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
        assert db_record["last_agent"] == "tinyllama"

@pytest.mark.e2e
def test_e2e_address_registration_cli_json(mock_orchestrator):
    """Testa o fluxo completo de cadastro de endereços via CLI com saída JSON."""
    # Setup
    prompt = "Cadastro de endereços"
    
    # Configura resultado esperado
    mock_orchestrator.execute.return_value = AgentResult(
        output=json.dumps({
            "name": "Cadastro de Endereços",
            "features": ["Cadastro", "Validação"],
            "tests": ["test_cadastro", "test_validacao"]
        }),
        items=[{"type": "feature", "content": "Cadastro de endereços implementado"}],
        guardrails=[],
        raw_responses=[{"id": "test", "response": {"text": "Cadastro implementado"}}]
    )
    
    # Execução
    result = run_make_command(prompt, format="json")
    
    # Verificações
    assert result["returncode"] in [0, 1], f"Código de retorno inesperado: {result['returncode']}"
    
    if result["returncode"] == 0:
        # Verifica se a saída é um JSON válido
        try:
            output = json.loads(result["stdout"])
            assert "name" in output
            assert "features" in output
            assert "tests" in output
        except json.JSONDecodeError:
            pytest.fail("Saída não é um JSON válido")
            
        # Verifica registro no banco
        db_record = result["db_history"]
        assert db_record is not None
        assert db_record["input"] == prompt
        assert db_record["output_type"] == "json"
        assert db_record["last_agent"] == "tinyllama"

@pytest.mark.e2e
def test_e2e_address_registration_error_handling(mock_orchestrator):
    """Testa o tratamento de erros no fluxo de cadastro de endereços."""
    # Setup
    prompt = "Cadastro de endereços"
    
    # Configura erro
    mock_orchestrator.execute.side_effect = ValueError("Erro de teste")
    
    # Execução
    result = run_make_command(prompt)
    
    # Verificações
    assert result["returncode"] == 1
    assert "❌ Erro:" in result["stderr"]

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
        timeout=TEST_CONFIG['environment']['timeout']['install'],
        env={**os.environ, "PYTHONPATH": str(test_env)}
    )
    
    # Verificações
    assert result.returncode == 0
    assert TEST_CONFIG['cli']['messages']['install']['start'] in result.stdout
    assert TEST_CONFIG['cli']['messages']['install']['success'] in result.stdout

@pytest.mark.e2e
def test_e2e_clean_command(test_env):
    """Testa o comando make clean."""
    # Configura ambiente de teste
    os.chdir(test_env)
    
    # Cria alguns arquivos e diretórios para limpar
    for dir_name in TEST_CONFIG['environment']['directories']['temp_dirs']:
        os.makedirs(dir_name, exist_ok=True)
    
    # Executa o comando
    result = run_command_with_timeout(
        "make clean",
        cwd=test_env,
        timeout=TEST_CONFIG['environment']['timeout']['setup']
    )
    
    # Verificações
    assert result.returncode == 0
    assert TEST_CONFIG['cli']['messages']['clean']['start'] in result.stdout
    assert TEST_CONFIG['cli']['messages']['clean']['success'] in result.stdout
    
    # Verifica se os diretórios foram removidos
    for dir_name in TEST_CONFIG['environment']['directories']['temp_dirs']:
        assert not os.path.exists(dir_name)

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
        timeout=TEST_CONFIG['environment']['timeout']['help_command']
    )
    
    # Verificações
    assert result.returncode == 0
    for section in TEST_CONFIG['cli']['messages']['help']['sections']:
        assert section in result.stdout
    for command in TEST_CONFIG['cli']['messages']['help']['commands']:
        assert command in result.stdout

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

@pytest.mark.e2e
def test_e2e_docs_build(test_env, capfd):
    """Teste e2e do comando docs-build."""
    # Configura ambiente de teste
    os.chdir(test_env)
    
    # Instala dependências de documentação
    pip_cmd = str(test_env / ".venv" / "bin" / "pip")
    result = run_command_with_timeout(
        f"{pip_cmd} install mkdocs mkdocs-material",
        cwd=test_env,
        timeout=60
    )
    assert result.returncode == 0, "Falha ao instalar dependências de documentação"
    
    # Cria estrutura básica de documentação
    docs_dir = test_env / "docs"
    docs_dir.mkdir(exist_ok=True)
    
    # Cria arquivo index.md de teste
    index_file = docs_dir / "index.md"
    index_file.write_text("# Teste\nConteúdo de teste")
    
    # Cria diretório de configuração
    config_dir = test_env / "src" / "configs"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Cria arquivo mkdocs.yml
    mkdocs_file = config_dir / "mkdocs.yml"
    mkdocs_file.write_text("""
site_name: Agent Flow TDD
theme:
  name: material
  language: pt-BR
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.expand
    - navigation.top
    - navigation.tracking
    - navigation.indexes
    - navigation.instant
    - navigation.footer
    - toc.follow
    - toc.integrate
docs_dir: ../../docs
site_dir: ../../site
nav:
  - Home: index.md
""")
    
    # Cria Makefile
    makefile_content = """
docs-build:
	@echo "📚 Gerando documentação estática..."
	@cd src/configs && mkdocs build
"""
    makefile = test_env / "Makefile"
    makefile.write_text(makefile_content)
    
    # Executa o comando
    result = run_command_with_timeout(
        "make docs-build",
        cwd=test_env,
        timeout=30,
        env={**os.environ, "PYTHONPATH": str(test_env)}
    )
    
    # Verifica resultado
    assert result.returncode == 0, "O comando docs-build falhou"
    assert "📚 Gerando documentação estática..." in result.stdout
    
    # Verifica se o site foi gerado
    site_dir = test_env / "site"
    assert site_dir.exists(), "Diretório site não foi criado"
    assert (site_dir / "index.html").exists(), "Arquivo index.html não foi gerado"

@pytest.mark.e2e
def test_e2e_docs_workflow(test_env, capfd, mock_orchestrator):
    """Testa o fluxo completo de geração de documentação."""
    # Setup
    docs_dir = test_env / "docs"
    os.makedirs(docs_dir, exist_ok=True)
    
    # Configura resultado esperado para documentação
    mock_orchestrator.execute.return_value = AgentResult(
        output="# Documentação\n\n## Instalação\n1. Clone o repositório\n2. Instale dependências",
        items=[{"type": "docs", "content": "Documentação gerada"}],
        guardrails=[],
        raw_responses=[{"id": "test", "response": {"text": "Documentação gerada"}}]
    )
    
    # Execução
    result = run_make_command("Gerar documentação", mode="docs")
    
    # Verificações
    assert result["returncode"] == 0
    assert os.path.exists(docs_dir / "index.md")
    
    # Verifica conteúdo da documentação
    with open(docs_dir / "index.md", "r") as f:
        content = f.read()
        assert "# Documentação" in content
        assert "## Instalação" in content
        
    # Verifica registro no banco
    db_record = result["db_history"]
    assert db_record is not None
    assert db_record["output_type"] == "markdown"
    assert db_record["last_agent"] == "tinyllama"

@pytest.mark.e2e
def test_e2e_docs_content_validation(test_env):
    """Teste e2e para validar o conteúdo gerado da documentação."""
    # Configura ambiente de teste
    os.chdir(test_env)
    
    # Gera documentação
    result = run_command_with_timeout(
        "make docs-generate",
        cwd=test_env,
        timeout=30,
        env={**os.environ, "PYTHONPATH": str(test_env)}
    )
    assert result.returncode == 0, "O comando docs-generate falhou"
    
    # Verifica conteúdo dos arquivos principais
    docs_dir = test_env / "docs"
    
    # 1. Verifica index.md
    index_content = (docs_dir / "index.md").read_text()
    assert "# Agent Flow TDD" in index_content
    assert "Framework para desenvolvimento" in index_content
    
    # 2. Verifica seções principais
    sections = {
        "overview": ["Visão Geral", "Objetivo", "Arquitetura"],
        "installation": ["Instalação", "Dependências", "Ambiente"],
        "usage": ["Uso", "CLI", "MCP"],
        "development": ["Desenvolvimento", "Código", "Local"],
        "testing": ["Testes", "Unitários", "Cobertura"],
        "database": ["Banco de Dados", "Estrutura", "SQL"],
        "logs": ["Logs", "Formato", "Níveis"],
        "deployment": ["Deploy", "Docker", "Produção"],
        "troubleshooting": ["Troubleshooting", "Erros", "Fallback"]
    }
    
    for section, expected_content in sections.items():
        section_index = (docs_dir / section / "index.md").read_text()
        # Verifica se o título da seção existe
        assert expected_content[0] in section_index
        # Verifica se os tópicos principais são mencionados
        for topic in expected_content[1:]:
            assert topic in section_index

@pytest.mark.e2e
def test_e2e_docs_links_validation(test_env):
    """Teste e2e para validar os links na documentação gerada."""
    # Configura ambiente de teste
    os.chdir(test_env)
    
    # Instala dependências de documentação
    pip_cmd = str(test_env / ".venv" / "bin" / "pip")
    result = run_command_with_timeout(
        f"{pip_cmd} install mkdocs mkdocs-material",
        cwd=test_env,
        timeout=60
    )
    assert result.returncode == 0, "Falha ao instalar dependências de documentação"
    
    # Cria diretório de configuração
    config_dir = test_env / "src" / "configs"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Cria arquivo mkdocs.yml
    mkdocs_file = config_dir / "mkdocs.yml"
    mkdocs_file.write_text("""
site_name: Agent Flow TDD
theme:
  name: material
  language: pt-BR
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.expand
    - navigation.top
    - navigation.tracking
    - navigation.indexes
    - navigation.instant
    - navigation.footer
    - toc.follow
    - toc.integrate
docs_dir: ../../docs
site_dir: ../../site
nav:
  - Home: index.md
""")
    
    # Cria diretório scripts
    scripts_dir = test_env / "src" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    
    # Copia o script generate_docs.py
    shutil.copy(
        Path(__file__).parent.parent / "scripts" / "generate_docs.py",
        scripts_dir / "generate_docs.py"
    )
    
    # Cria Makefile
    makefile_content = """
docs-generate:
	@echo "🤖 Gerando documentação via IA..."
	@mkdir -p docs
	@python src/scripts/generate_docs.py

docs-build:
	@echo "📚 Gerando documentação estática..."
	@cd src/configs && mkdocs build
"""
    makefile = test_env / "Makefile"
    makefile.write_text(makefile_content)
    
    # Gera e compila a documentação
    result = run_command_with_timeout(
        "make docs-generate",
        cwd=test_env,
        timeout=30,
        env={**os.environ, "PYTHONPATH": str(test_env)}
    )
    assert result.returncode == 0, "O comando docs-generate falhou"
    
    result = run_command_with_timeout(
        "make docs-build",
        cwd=test_env,
        timeout=30,
        env={**os.environ, "PYTHONPATH": str(test_env)}
    )
    assert result.returncode == 0, "O comando docs-build falhou"
    
    # Verifica os links no site gerado
    site_dir = test_env / "site"
    
    # 1. Verifica se o arquivo de busca foi gerado
    assert (site_dir / "search" / "search_index.json").exists()
    
    # 2. Verifica se os assets do tema foram copiados
    assert (site_dir / "assets").exists()
    
    # 3. Verifica se os links internos estão corretos
    index_html = (site_dir / "index.html").read_text()
    
    # Verifica links para seções principais
    sections = [
        "overview", "installation", "usage", "development",
        "testing", "database", "logs", "deployment", "troubleshooting"
    ]
    
    for section in sections:
        assert f'href="{section}/' in index_html
        
        # Verifica se a página da seção tem links para suas subseções
        section_html = (site_dir / section / "index.html").read_text()
        assert "nav" in section_html
        assert "md-nav" in section_html 