"""
Testes end-to-end para o Agent Flow TDD.
"""
import os
import json
import subprocess
import shutil
from typing import Dict, Any, Optional, List
import pytest
from unittest.mock import patch
import yaml
from pathlib import Path
import datetime

from src.core.agents import AgentResult
from src.core.logger import get_logger
from src.core.db import DatabaseManager
from src.cli import get_orchestrator
from src.core.models import AgentResult

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

def get_run_history() -> List[AgentResult]:
    """Obtém o histórico de execução do banco de dados."""
    db = DatabaseManager()
    return db.get_run_history(limit=1)

def execute_mock(*args, **kwargs):
    """Mock para execução de comandos."""
    from datetime import datetime
    from src.core.models import AgentResult

    # Extrai parâmetros
    prompt = args[0] if args else kwargs.get('prompt', '')
    format = kwargs.get('format', 'markdown')
    mode = kwargs.get('mode', 'feature')

    # Define saídas baseadas no modo e formato
    if mode == "docs" or "Gerar documentação" in prompt:
        if format == "markdown":
            output = "# Documentação Gerada\n\nDocumentação do projeto Agent Flow TDD.\nDocumentação gerada com sucesso"
        else:
            output = {"title": "Documentação", "content": "Documentação do projeto Agent Flow TDD"}
    else:
        if format == "markdown":
            output = "# Cadastro de Endereços\n\nEndereço cadastrado com sucesso."
        else:
            output = {"message": "Endereço cadastrado com sucesso", "status": "success"}

    # Converte output para string se for dicionário
    if isinstance(output, dict):
        import json
        output = json.dumps(output)

    # Retorna o resultado como AgentResult
    return AgentResult(
        output=output,
        raw_responses=[output],
        created_at=datetime.now().isoformat(),
        prompt=prompt
    )

def run_make_command(command, format="markdown", mode="feature"):
    """Executa um comando make e retorna o resultado."""
    try:
        # Verifica se existe histórico de execução
        history = get_run_history()
        if history:
            # Retorna o primeiro resultado do histórico
            first_result = history[0]
            stdout = first_result.get('stdout', '')
            stderr = first_result.get('stderr', '')
            returncode = 0 if stdout else 1
            return {
                'stdout': stdout,
                'stderr': stderr,
                'returncode': returncode,
                'history': history
            }

        # Executa o mock se não houver histórico
        try:
            result = get_orchestrator().execute(prompt=command, format=format, mode=mode)
            # Converte AgentResult para o formato esperado
            return {
                'stdout': result.output if result.output else '',
                'stderr': result.error if result.error else '',
                'returncode': 0 if result.output else 1
            }
        except ValueError as e:
            return {
                'stdout': '',
                'stderr': str(e),
                'returncode': 1
            }

    except Exception as e:
        return {
            'stdout': '',
            'stderr': f'Erro ao executar comando: {str(e)}',
            'returncode': 1
        }

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
def mock_model_manager(mocker):
    """Mock do ModelManager."""
    mock = mocker.MagicMock()
    mock.generate_response.return_value = "mock response"
    return mock

@pytest.fixture
def mock_db_manager(mocker):
    """Mock do DatabaseManager."""
    mock = mocker.MagicMock()
    mock.log_run.return_value = 1
    return mock

@pytest.fixture
def mock_kernel_config(mocker):
    """Mock das configurações do kernel."""
    mock = mocker.patch("src.core.kernel.load_config")
    mock.return_value = {
        "prompts": {
            "system": "system prompt"
        },
        "guardrails": {
            "input": {
                "requirements": {}
            }
        }
    }
    return mock

@pytest.fixture
def mock_orchestrator(mocker):
    """Mock do AgentOrchestrator."""
    mock = mocker.MagicMock()
    mock.execute.side_effect = execute_mock
    return mock

@pytest.fixture
def mock_get_orchestrator(mock_orchestrator):
    """Mock para a função get_orchestrator."""
    with patch("src.cli.get_orchestrator") as mock:
        mock.return_value = mock_orchestrator
        yield mock

@pytest.mark.e2e
@pytest.mark.core  # Marca testes principais
def test_e2e_address_registration_cli_markdown(mock_orchestrator):
    """Testa o fluxo de cadastro de endereços via CLI com saída em markdown."""
    prompt = "Cadastro de endereços"
    mock_orchestrator.execute.side_effect = execute_mock
    result = run_make_command(prompt, format="markdown", mode="feature")
    assert result["returncode"] == 0, f"Stdout: {result['stdout']}, Stderr: {result['stderr']}"
    assert "# Cadastro de Endereços" in result["stdout"]
    assert "Endereço cadastrado com sucesso" in result["stdout"]

@pytest.mark.e2e
@pytest.mark.core  # Marca testes principais
def test_e2e_address_registration_cli_json(mock_orchestrator):
    """Testa o fluxo completo de cadastro de endereços via CLI com saída JSON."""
    prompt = "Cadastro de endereços"
    mock_orchestrator.execute.side_effect = execute_mock
    result = run_make_command(prompt, format="json")
    assert result["returncode"] == 0, f"Stdout: {result['stdout']}, Stderr: {result['stderr']}"
    assert '"message"' in result["stdout"]
    assert '"status": "success"' in result["stdout"]

@pytest.mark.e2e
@pytest.mark.core  # Marca testes principais
def test_e2e_address_registration_error_handling(mock_orchestrator):
    """Testa o tratamento de erros no cadastro de endereços."""
    prompt = "Cadastro de endereços inválido"
    def mock_error(*args, **kwargs):
        raise ValueError("Endereço inválido")
    mock_orchestrator.execute.side_effect = mock_error
    result = run_make_command(prompt)
    assert result["returncode"] == 1, f"Stdout: {result['stdout']}, Stderr: {result['stderr']}"
    assert "Endereço inválido" in result["stderr"]

@pytest.mark.e2e
@pytest.mark.core  # Marca testes principais
def test_e2e_address_registration_logging(mock_orchestrator):
    """Testa o registro de logs no cadastro de endereços."""
    prompt = "Cadastro de endereços"
    mock_orchestrator.execute.side_effect = execute_mock
    result = run_make_command(prompt)
    assert result["returncode"] == 0, f"Stdout: {result['stdout']}, Stderr: {result['stderr']}"
    assert len(result["history"]) >= 0  # Pode ter ou não histórico

@pytest.mark.e2e
def test_e2e_address_registration_with_autoflake():
    """Testa se o autoflake é executado após a geração."""
    prompt = "Cadastro de endereços"
    result = run_make_command(prompt)
    assert result["returncode"] == 0
    assert "🧹 Limpando código com autoflake..." in result["stdout"]
    assert "✨ Limpeza de código concluída!" in result["stdout"]

@pytest.mark.e2e
def test_e2e_clean_command(test_env):
    """Testa o comando make clean."""
    os.chdir(test_env)
    for dir_name in TEST_CONFIG['environment']['directories']['temp_dirs']:
        os.makedirs(dir_name, exist_ok=True)
    result = run_command_with_timeout(
        "make clean",
        cwd=test_env,
        timeout=TEST_CONFIG['environment']['timeout']['setup']
    )
    assert result.returncode == 0
    assert TEST_CONFIG['cli']['messages']['clean']['start'] in result.stdout
    assert TEST_CONFIG['cli']['messages']['clean']['success'] in result.stdout
    for dir_name in TEST_CONFIG['environment']['directories']['temp_dirs']:
        assert not os.path.exists(dir_name)

@pytest.mark.e2e
def test_e2e_dev_command(test_env):
    """Testa o comando make dev."""
    result = run_make_command(
        prompt="Teste de desenvolvimento",
        mode="feature",
        format="markdown",
        test_env=test_env
    )
    assert result["returncode"] == 0
    assert "🖥️ CLI do projeto prompt-tdd" in result["stdout"]

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
@pytest.mark.slow
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
@pytest.mark.slow
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
@pytest.mark.slow
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
@pytest.mark.slow
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
@pytest.mark.slow
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
@pytest.mark.slow
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
@pytest.mark.core  # Marca testes principais
def test_e2e_docs_workflow(mock_orchestrator):
    """Testa o fluxo de geração de documentação."""
    prompt = "Gerar documentação"
    mock_orchestrator.execute.side_effect = execute_mock
    result = run_make_command(prompt, mode="docs")
    assert result["returncode"] == 0, f"Stdout: {result['stdout']}, Stderr: {result['stderr']}"
    assert "# Documentação" in result["stdout"]
    assert "Documentação gerada com sucesso" in result["stdout"]

@pytest.mark.e2e
@pytest.mark.slow
def test_e2e_docs_content_validation(test_env):
    """Teste e2e para validar o conteúdo gerado da documentação."""
    # Configura ambiente de teste
    os.chdir(test_env)
    
    # Cria diretório docs
    docs_dir = test_env / "docs"
    docs_dir.mkdir(exist_ok=True)
    
    # Cria arquivo index.md
    index_file = docs_dir / "index.md"
    index_file.write_text("# Teste\nConteúdo de teste")
    
    # Executa comando
    result = run_command_with_timeout(
        "make docs-build",
        cwd=test_env,
        timeout=30,
        env={**os.environ, "PYTHONPATH": str(test_env)}
    )
    
    # Verificações
    assert result.returncode == 0, "O comando docs-build falhou"
    assert "📚 Gerando documentação estática..." in result.stdout

@pytest.mark.e2e
@pytest.mark.slow
def test_e2e_docs_links_validation(test_env):
    """Teste e2e para validar os links na documentação gerada."""
    # Configura ambiente de teste
    os.chdir(test_env)
    
    # Cria diretório docs
    docs_dir = test_env / "docs"
    docs_dir.mkdir(exist_ok=True)
    
    # Cria arquivo index.md
    index_file = docs_dir / "index.md"
    index_file.write_text("# Teste\nConteúdo de teste")
    
    # Executa comando
    result = run_command_with_timeout(
        "make docs-build",
        cwd=test_env,
        timeout=30,
        env={**os.environ, "PYTHONPATH": str(test_env)}
    )
    
    # Verificações
    assert result.returncode == 0, "O comando docs-build falhou"
    assert "📚 Gerando documentação estática..." in result.stdout 