"""
Módulo de gerenciamento do banco de dados.
"""
import json
import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Gerenciador do banco de dados SQLite."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Inicializa o gerenciador.
        
        Args:
            db_path: Caminho para o banco de dados
        """
        # Cria diretório de logs se não existir
        os.makedirs("logs", exist_ok=True)
        
        # Define caminho do banco
        self.db_path = db_path or "logs/agent_logs.db"
        
        # Conecta ao banco
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        # Cria tabelas
        self._create_tables()
        
    def _create_tables(self):
        """Cria as tabelas do banco de dados."""
        cursor = self.conn.cursor()
        
        # Tabela principal de execuções
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            session_id TEXT NOT NULL,
            input TEXT NOT NULL,
            last_agent TEXT,
            output_type TEXT,
            final_output TEXT
        )
        """)
        
        # Tabela de itens gerados
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS run_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            item_type TEXT NOT NULL,
            raw_item TEXT NOT NULL,
            source_agent TEXT,
            target_agent TEXT,
            FOREIGN KEY(run_id) REFERENCES agent_runs(id)
        )
        """)
        
        # Tabela de resultados de guardrails
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS guardrail_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            guardrail_type TEXT CHECK(guardrail_type IN ('input', 'output')),
            results TEXT NOT NULL,
            FOREIGN KEY(run_id) REFERENCES agent_runs(id)
        )
        """)
        
        # Tabela de respostas brutas do LLM
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS raw_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            response TEXT NOT NULL,
            FOREIGN KEY(run_id) REFERENCES agent_runs(id)
        )
        """)
        
        self.conn.commit()
    
    def log_run(self, session_id: str, input: str, final_output: Optional[str] = None,
                last_agent: Optional[str] = None, output_type: Optional[str] = None) -> int:
        """
        Registra uma execução do agente.
        
        Args:
            session_id: ID da sessão
            input: Texto de entrada
            final_output: Saída final
            last_agent: Último agente executado
            output_type: Tipo de saída
            
        Returns:
            ID da execução registrada
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
        INSERT INTO agent_runs (session_id, input, final_output, last_agent, output_type)
        VALUES (?, ?, ?, ?, ?)
        """, (session_id, input, final_output, last_agent, output_type))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def log_run_item(self, run_id: int, item_type: str, raw_item: Dict[str, Any],
                     source_agent: Optional[str] = None, target_agent: Optional[str] = None):
        """
        Registra um item gerado durante a execução.
        
        Args:
            run_id: ID da execução
            item_type: Tipo do item
            raw_item: Item bruto
            source_agent: Agente de origem
            target_agent: Agente de destino
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
        INSERT INTO run_items (run_id, item_type, raw_item, source_agent, target_agent)
        VALUES (?, ?, ?, ?, ?)
        """, (run_id, item_type, json.dumps(raw_item), source_agent, target_agent))
        
        self.conn.commit()
    
    def log_guardrail_results(self, run_id: int, guardrail_type: str, results: Dict[str, Any]):
        """
        Registra resultados de guardrails.
        
        Args:
            run_id: ID da execução
            guardrail_type: Tipo do guardrail (input/output)
            results: Resultados do guardrail
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
        INSERT INTO guardrail_results (run_id, guardrail_type, results)
        VALUES (?, ?, ?)
        """, (run_id, guardrail_type, json.dumps(results)))
        
        self.conn.commit()
    
    def log_raw_response(self, run_id: int, response: Dict[str, Any]):
        """
        Registra uma resposta bruta do LLM.
        
        Args:
            run_id: ID da execução
            response: Resposta do LLM
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
        INSERT INTO raw_responses (run_id, response)
        VALUES (?, ?)
        """, (run_id, json.dumps(response)))
        
        self.conn.commit()
    
    def get_run_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retorna o histórico das últimas execuções.
        
        Args:
            limit: Número máximo de registros
            
        Returns:
            Lista de execuções com seus detalhes
        """
        cursor = self.conn.cursor()
        
        # Busca execuções
        cursor.execute("""
        SELECT * FROM agent_runs
        ORDER BY timestamp DESC
        LIMIT ?
        """, (limit,))
        
        runs = []
        for run in cursor.fetchall():
            run_dict = dict(run)
            
            # Busca itens
            cursor.execute("SELECT * FROM run_items WHERE run_id = ?", (run['id'],))
            run_dict['items'] = [dict(item) for item in cursor.fetchall()]
            
            # Busca guardrails
            cursor.execute("SELECT * FROM guardrail_results WHERE run_id = ?", (run['id'],))
            run_dict['guardrails'] = [dict(guard) for guard in cursor.fetchall()]
            
            # Busca respostas brutas
            cursor.execute("SELECT * FROM raw_responses WHERE run_id = ?", (run['id'],))
            run_dict['raw_responses'] = [dict(resp) for resp in cursor.fetchall()]
            
            runs.append(run_dict)
        
        return runs
    
    def close(self):
        """Fecha a conexão com o banco."""
        self.conn.close()