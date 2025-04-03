"""
Testes end-to-end para o Agent Flow TDD.
"""
import os
import json
import subprocess
from typing import Dict, Any
import pytest

from src.core.db import DatabaseManager
from src.core.logger import setup_logger

logger = setup_logger(__name__)

def run_make_command(prompt: str, mode: str = "cli", format: str = "markdown") -> Dict[str, Any]:
    """
    Executa o comando make dev e retorna o resultado.
    
    Args:
        prompt: Prompt para o TDD
        mode: Modo de execução
        format: Formato de saída
        
    Returns:
        Dicionário com resultado da execução
    """
    try:
        # Executa o comando make
        cmd = f'make dev prompt-tdd="{prompt}" mode={mode} format={format}'
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True
        )
        
        # Verifica logs no banco
        db = DatabaseManager()
        history = db.get_run_history(limit=1)
        db.close()
        
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "db_history": history[0] if history else None
        }
    except subprocess.CalledProcessError as e:
        return {
            "stdout": e.stdout,
            "stderr": e.stderr,
            "returncode": e.returncode,
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
    assert result["returncode"] == 0
    assert "🛠️ Executando CLI em modo desenvolvimento..." in result["stdout"]
    
    # Verifica registro no banco
    db_record = result["db_history"]
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
    assert result["returncode"] == 0
    
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
        assert result["returncode"] != 0  # Qualquer código de erro é válido
        assert "Erro ao processar comando" in result["stdout"]
        
    finally:
        # Restaura a chave
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
    assert result["returncode"] == 0
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
    assert result["returncode"] == 0
    
    # Verifica se os logs foram registrados no banco
    db_record = result["db_history"]
    assert db_record is not None
    assert len(db_record["raw_responses"]) > 0  # Deve ter pelo menos uma resposta logada
    
    # Verifica se a resposta contém os campos esperados
    raw_response = db_record["raw_responses"][0]
    assert "id" in raw_response
    assert "response" in raw_response
    assert isinstance(raw_response["response"], str)  # Deve ser um JSON serializado 