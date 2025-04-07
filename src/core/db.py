"""
Módulo de gerenciamento do banco de dados.
"""
import json
import logging
import os
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple
import yaml

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Gerenciador de banco de dados."""
    
    def __init__(self, db_path: str = None):
        """
        Inicializa o gerenciador de banco de dados.
        
        Args:
            db_path: Caminho para o arquivo de banco de dados
        """
        self.db_path = db_path or "logs/agent_logs.db"
        
        # Cria diretório se não existir e não for banco em memória
        if self.db_path != ":memory:":
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
        # Inicializa conexão
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        # Cria tabelas
        self._create_tables()
        logger.info(f"Banco de dados inicializado em {self.db_path}")
        
    def _create_tables(self):
        """Cria as tabelas do banco de dados."""
        cursor = self.conn.cursor()
        
        # Tabela de execuções
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                prompt TEXT NOT NULL,
                format TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabela de itens de execução
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS run_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES runs (id)
            )
        """)
        
        # Tabela de resultados de guardrails
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS guardrail_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                passed BOOLEAN NOT NULL,
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES runs (id)
            )
        """)
        
        # Tabela de respostas brutas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS raw_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                response_id TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES runs (id)
            )
        """)
        
        # Tabela de cache de modelos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model TEXT NOT NULL,
                prompt TEXT NOT NULL,
                response TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(model, prompt)
            )
        """)
        
        self.conn.commit()
        logger.info("Tabelas criadas/verificadas")
        
    def get_cached_response(self, cache_key: str, ttl: int) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Obtém uma resposta do cache se disponível e não expirada.
        
        Args:
            cache_key: Chave de cache
            ttl: Tempo de vida em segundos
            
        Returns:
            Tupla (resposta, metadados) se encontrada e válida, None caso contrário
        """
        cursor = self.conn.cursor()
        
        # Busca resposta não expirada
        cursor.execute("""
        SELECT response, metadata, timestamp
        FROM model_cache
        WHERE cache_key = ?
        """, (cache_key,))
        
        row = cursor.fetchone()
        if row is None:
            return None
            
        # Verifica TTL
        timestamp = time.mktime(time.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S'))
        if time.time() - timestamp > ttl:
            # Remove resposta expirada
            cursor.execute("DELETE FROM model_cache WHERE cache_key = ?", (cache_key,))
            self.conn.commit()
            return None
            
        return json.loads(row['response']), json.loads(row['metadata'])
        
    def save_to_cache(self, cache_key: str, response: str, metadata: Dict[str, Any]):
        """
        Salva uma resposta no cache.
        
        Args:
            cache_key: Chave de cache
            response: Resposta do modelo
            metadata: Metadados da resposta
        """
        cursor = self.conn.cursor()
        
        # Remove entrada anterior se existir
        cursor.execute("DELETE FROM model_cache WHERE cache_key = ?", (cache_key,))
        
        # Insere nova entrada
        cursor.execute("""
        INSERT INTO model_cache (cache_key, response, metadata)
        VALUES (?, ?, ?)
        """, (cache_key, json.dumps(response), json.dumps(metadata)))
        
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
        INSERT INTO runs (session_id, prompt, format)
        VALUES (?, ?, ?)
        """, (session_id, input, output_type))
        
        run_id = cursor.lastrowid
        
        cursor.execute("""
        INSERT INTO run_items (run_id, type, content)
        VALUES (?, ?, ?)
        """, (run_id, "input", input))
        
        cursor.execute("""
        INSERT INTO guardrail_results (run_id, type, passed)
        VALUES (?, ?, ?)
        """, (run_id, "input", final_output is not None))
        
        cursor.execute("""
        INSERT INTO raw_responses (run_id, response_id, content)
        VALUES (?, ?, ?)
        """, (run_id, "input", json.dumps(final_output if final_output else {})))
        
        self.conn.commit()
        return run_id
        
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
        INSERT INTO run_items (run_id, type, content)
        VALUES (?, ?, ?)
        """, (run_id, item_type, json.dumps(raw_item)))
        
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
        INSERT INTO guardrail_results (run_id, type, passed)
        VALUES (?, ?, ?)
        """, (run_id, guardrail_type, results["passed"]))
        
        cursor.execute("""
        INSERT INTO raw_responses (run_id, response_id, content)
        VALUES (?, ?, ?)
        """, (run_id, guardrail_type, json.dumps(results["results"])))
        
        self.conn.commit()
        
    def log_raw_response(self, run_id: int, response: Dict[str, Any]):
        """
        Registra uma resposta bruta do modelo.
        
        Args:
            run_id: ID da execução
            response: Resposta do modelo
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
        INSERT INTO raw_responses (run_id, response_id, content)
        VALUES (?, ?, ?)
        """, (run_id, "output", json.dumps(response)))
        
        self.conn.commit()
        
    def get_run_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtém o histórico de execuções.
        
        Args:
            limit: Limite de registros a retornar
            
        Returns:
            Lista de execuções com seus itens e resultados
        """
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
            SELECT 
                r.id,
                r.session_id,
                r.prompt,
                r.format,
                r.created_at,
                GROUP_CONCAT(DISTINCT i.content) as items,
                GROUP_CONCAT(DISTINCT g.type || ':' || g.passed) as guardrails,
                GROUP_CONCAT(DISTINCT rr.content) as responses
            FROM runs r
            LEFT JOIN run_items i ON i.run_id = r.id
            LEFT JOIN guardrail_results g ON g.run_id = r.id
            LEFT JOIN raw_responses rr ON rr.run_id = r.id
            GROUP BY r.id
            ORDER BY r.created_at DESC
            LIMIT ?
            """, (limit,))
            
            runs = []
            for row in cursor.fetchall():
                run = dict(row)
                
                # Processa itens
                items = []
                if run["items"]:
                    items = [{"content": item} for item in run["items"].split(",")]
                run["items"] = items
                
                # Processa guardrails
                guardrails = []
                if run["guardrails"]:
                    for g in run["guardrails"].split(","):
                        type_, passed = g.split(":")
                        guardrails.append({
                            "type": type_,
                            "passed": passed == "1"
                        })
                run["guardrails"] = guardrails
                
                # Processa respostas
                responses = []
                if run["responses"]:
                    responses = [json.loads(r) for r in run["responses"].split(",")]
                run["responses"] = responses
                
                runs.append(run)
                
            return runs
            
        except sqlite3.Error as e:
            logger.error(f"FALHA - get_run_history | Erro: {str(e)}")
            raise

    def get_runs(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Lista execuções registradas.

        Args:
            limit: Limite de registros

        Returns:
            Lista de execuções
        """
        cursor = self.conn.cursor()

        # Monta SQL base
        sql = """
        SELECT r.*, i.content as raw_item, g.content as guardrail_results, rr.content as raw_response
        FROM runs r
        LEFT JOIN run_items i ON r.id = i.run_id
        LEFT JOIN guardrail_results g ON r.id = g.run_id
        LEFT JOIN raw_responses rr ON r.id = rr.run_id
        """

        # Adiciona ordenação e limite
        sql += " ORDER BY r.created_at DESC"
        if limit is not None:
            sql += " LIMIT ?"
            cursor.execute(sql, (limit,))
        else:
            cursor.execute(sql)

        # Processa resultados
        runs = []
        for row in cursor.fetchall():
            run = dict(row)
            
            # Converte strings JSON
            if run["raw_item"]:
                run["raw_item"] = json.loads(run["raw_item"])
            if run["guardrail_results"]:
                run["guardrail_results"] = json.loads(run["guardrail_results"])
            if run["raw_response"]:
                run["raw_response"] = json.loads(run["raw_response"])
            
            runs.append(run)

        return runs