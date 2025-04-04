"""
Módulo de gerenciamento do banco de dados.
"""
import json
import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional
import yaml

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Gerenciador do banco de dados SQLite."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Inicializa o gerenciador.
        
        Args:
            db_path: Caminho para o banco de dados
        """
        # Carrega configurações
        config_path = os.path.join("src", "configs", "database.yaml")
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
        
        # Cria diretório de logs se não existir
        os.makedirs(self.config["directories"]["logs"], exist_ok=True)
        
        # Define caminho do banco
        self.db_path = db_path or self.config["database"]["default_path"]
        
        # Conecta ao banco
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        # Cria tabelas
        self._create_tables()
        
    def _create_tables(self):
        """Cria as tabelas do banco de dados."""
        cursor = self.conn.cursor()
        
        for table_name, table_config in self.config["tables"].items():
            # Monta SQL para colunas
            columns = []
            for col in table_config["columns"]:
                columns.append(f"{col['name']} {col['type']}")
            
            # Adiciona foreign keys
            if "foreign_keys" in table_config:
                for fk in table_config["foreign_keys"]:
                    columns.append(f"FOREIGN KEY({fk['column']}) REFERENCES {fk['references']}")
            
            # Adiciona checks
            if "checks" in table_config:
                for check in table_config["checks"]:
                    columns.append(f"CHECK({check['column']} {check['constraint']})")
            
            # Monta e executa SQL final
            sql = f"""
            CREATE TABLE IF NOT EXISTS {table_config['name']} (
                {', '.join(columns)}
            )
            """
            cursor.execute(sql)
        
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
    
    def get_run_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retorna o histórico das últimas execuções.
        
        Args:
            limit: Número máximo de registros. Se None, usa o valor padrão da configuração.
            
        Returns:
            Lista de execuções com seus detalhes, ordenada por timestamp decrescente
        """
        cursor = self.conn.cursor()
        
        # Usa limite da configuração se não especificado
        if limit is None:
            limit = self.config["database"]["history_limit"]
        
        # Busca execuções
        cursor.execute("""
        SELECT * FROM agent_runs
        ORDER BY id DESC
        LIMIT ?
        """, (limit,))
        
        runs = []
        for run in cursor.fetchall():
            run_dict = dict(run)
            
            # Busca itens
            cursor.execute("SELECT * FROM run_items WHERE run_id = ? ORDER BY id DESC", (run['id'],))
            run_dict['items'] = [dict(item) for item in cursor.fetchall()]
            
            # Busca guardrails
            cursor.execute("SELECT * FROM guardrail_results WHERE run_id = ? ORDER BY id DESC", (run['id'],))
            run_dict['guardrails'] = [dict(guardrail) for guardrail in cursor.fetchall()]
            
            # Busca respostas brutas
            cursor.execute("SELECT * FROM raw_responses WHERE run_id = ? ORDER BY id DESC", (run['id'],))
            run_dict['raw_responses'] = [dict(response) for response in cursor.fetchall()]
            
            runs.append(run_dict)
        
        return runs
    
    def close(self):
        """Fecha a conexão com o banco."""
        self.conn.close()