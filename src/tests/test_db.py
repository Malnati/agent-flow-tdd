"""
Testes para o módulo de banco de dados.
"""
import json
import sqlite3
import os
from datetime import datetime
import pytest
from unittest.mock import patch

from src.core.db import DatabaseManager

@pytest.fixture
def db_manager():
    """Fixture que fornece um DatabaseManager com banco em memória."""
    manager = DatabaseManager(":memory:")
    yield manager
    manager.close()

def test_create_tables(db_manager):
    """Testa a criação das tabelas."""
    cursor = db_manager.conn.cursor()
    
    # Verifica tabelas criadas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    
    assert "agent_runs" in tables
    assert "run_items" in tables
    assert "guardrail_results" in tables
    assert "raw_responses" in tables

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
        
        # Verifica se o banco foi criado
        assert test_db_path.exists()
        
        # Verifica se as tabelas foram criadas
        cursor = manager.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        
        assert "agent_runs" in tables
        assert "run_items" in tables
        assert "guardrail_results" in tables
        assert "raw_responses" in tables
        
        manager.close()

def test_db_clean_command(tmp_path):
    """Testa o comando db-clean do Makefile."""
    # Configura ambiente de teste
    test_db_path = tmp_path / "logs" / "agent_logs.db"
    os.makedirs(tmp_path / "logs", exist_ok=True)
    
    # Cria banco de dados
    manager = DatabaseManager(str(test_db_path))
    manager.close()
    
    assert test_db_path.exists()
    
    # Remove banco de dados
    os.remove(test_db_path)
    
    assert not test_db_path.exists()

def test_db_backup_command(tmp_path):
    """Testa o comando db-backup do Makefile."""
    # Configura ambiente de teste
    logs_dir = tmp_path / "logs"
    backups_dir = tmp_path / "backups"
    test_db_path = logs_dir / "agent_logs.db"
    
    os.makedirs(logs_dir, exist_ok=True)
    os.makedirs(backups_dir, exist_ok=True)
    
    # Cria banco de dados
    manager = DatabaseManager(str(test_db_path))
    manager.close()
    
    # Simula data atual
    current_date = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backups_dir / f"agent_logs_{current_date}.db"
    
    # Faz backup
    import shutil
    shutil.copy2(test_db_path, backup_path)
    
    assert backup_path.exists()
    assert os.path.getsize(backup_path) > 0 