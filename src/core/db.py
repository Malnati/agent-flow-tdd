"""
Módulo de gerenciamento de banco de dados SQLite para logging estruturado.
"""
import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path


from rich.table import Table
from rich.panel import Panel
from rich.text import Text

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Gerenciador de banco de dados SQLite para logging estruturado."""
    
    def __init__(self, db_path: str = "logs/agent_logs.db"):
        """
        Inicializa o gerenciador de banco de dados.
        
        Args:
            db_path: Caminho para o arquivo do banco de dados SQLite
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self._create_tables()
        logger.info(f"DatabaseManager inicializado: {db_path}")

    def _create_tables(self):
        """Cria as tabelas necessárias no banco de dados."""
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
        
        # Índices para otimização
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_runs_timestamp ON agent_runs(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_run_id ON run_items(run_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_type ON run_items(item_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_guardrails_run_id ON guardrail_results(run_id)")
        
        self.conn.commit()
        logger.debug("Tabelas criadas/verificadas com sucesso")

    def log_run(self, session_id: str, input_text: str, last_agent: Optional[str] = None,
                output_type: Optional[str] = None, final_output: Optional[str] = None) -> int:
        """
        Registra uma nova execução do agente.
        
        Args:
            session_id: ID da sessão
            input_text: Texto de entrada
            last_agent: Nome do último agente executado
            output_type: Tipo de saída do último agente
            final_output: Saída final da execução
            
        Returns:
            ID da execução registrada
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO agent_runs (session_id, input, last_agent, output_type, final_output)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, input_text, last_agent, output_type, final_output))
            self.conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Erro ao registrar execução: {str(e)}")
            raise

    def log_run_item(self, run_id: int, item_type: str, raw_item: Dict[str, Any],
                     source_agent: Optional[str] = None, target_agent: Optional[str] = None):
        """
        Registra um item gerado durante a execução.
        
        Args:
            run_id: ID da execução
            item_type: Tipo do item (MessageOutput, HandoffCall, etc)
            raw_item: Item bruto gerado
            source_agent: Agente de origem (para handoffs)
            target_agent: Agente de destino (para handoffs)
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO run_items (run_id, item_type, raw_item, source_agent, target_agent)
                VALUES (?, ?, ?, ?, ?)
            """, (run_id, item_type, json.dumps(raw_item), source_agent, target_agent))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Erro ao registrar item: {str(e)}")
            raise

    def log_guardrail_results(self, run_id: int, guardrail_type: str, results: Dict[str, Any]):
        """
        Registra resultados de guardrails.
        
        Args:
            run_id: ID da execução
            guardrail_type: Tipo do guardrail (input/output)
            results: Resultados do guardrail
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO guardrail_results (run_id, guardrail_type, results)
                VALUES (?, ?, ?)
            """, (run_id, guardrail_type, json.dumps(results)))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Erro ao registrar resultados de guardrail: {str(e)}")
            raise

    def log_raw_response(self, run_id: int, response: Dict[str, Any]):
        """
        Registra uma resposta bruta do LLM.
        
        Args:
            run_id: ID da execução
            response: Resposta bruta do modelo
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO raw_responses (run_id, response)
                VALUES (?, ?)
            """, (run_id, json.dumps(response)))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Erro ao registrar resposta bruta: {str(e)}")
            raise

    def get_run_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retorna o histórico das últimas execuções.
        
        Args:
            limit: Número máximo de registros a retornar
            
        Returns:
            Lista de execuções com seus itens e resultados
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT * FROM agent_runs
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            runs = []
            for row in cursor.fetchall():
                run = {
                    "id": row[0],
                    "timestamp": row[1],
                    "session_id": row[2],
                    "input": row[3],
                    "last_agent": row[4],
                    "output_type": row[5],
                    "final_output": row[6],
                    "items": [],
                    "guardrails": [],
                    "raw_responses": []
                }
                
                # Busca itens relacionados
                cursor.execute("SELECT * FROM run_items WHERE run_id = ?", (row[0],))
                run["items"] = [dict(zip(["id", "run_id", "timestamp", "item_type", "raw_item", 
                                        "source_agent", "target_agent"], item))
                              for item in cursor.fetchall()]
                
                # Busca resultados de guardrails
                cursor.execute("SELECT * FROM guardrail_results WHERE run_id = ?", (row[0],))
                run["guardrails"] = [dict(zip(["id", "run_id", "timestamp", "guardrail_type", 
                                             "results"], guard))
                                   for guard in cursor.fetchall()]
                
                # Busca respostas brutas
                cursor.execute("SELECT * FROM raw_responses WHERE run_id = ?", (row[0],))
                run["raw_responses"] = [dict(zip(["id", "run_id", "timestamp", "response"], resp))
                                      for resp in cursor.fetchall()]
                
                runs.append(run)
            
            return runs
            
        except Exception as e:
            logger.error(f"Erro ao buscar histórico: {str(e)}")
            raise

    def close(self):
        """Fecha a conexão com o banco de dados."""
        self.conn.close()
        logger.debug("Conexão com banco de dados fechada") 

    def format_timestamp(timestamp: str) -> str:
        """Formata timestamp para exibição."""
        try:
            dt = datetime.fromisoformat(timestamp)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return timestamp

    def format_json(data: str) -> str:
        """Formata JSON para exibição."""
        try:
            parsed = json.loads(data)
            return json.dumps(parsed, indent=2)
        except:
            return data

    def show_run_details(run: Dict[str, Any]):
        """Mostra detalhes de uma execução."""
        # Cabeçalho
        console.print(Panel(
            f"[bold blue]Execução {run['id']}[/bold blue]\n"
            f"Session: {run['session_id']}\n"
            f"Timestamp: {format_timestamp(run['timestamp'])}\n"
            f"Agente: {run['last_agent'] or 'N/A'}\n"
            f"Tipo de Saída: {run['output_type'] or 'N/A'}"
        ))
        
        # Input/Output
        console.print("\n[bold]Input:[/bold]")
        console.print(run['input'])
        if run['final_output']:
            console.print("\n[bold]Output:[/bold]")
            console.print(format_json(run['final_output']))
        
        # Itens gerados
        if run['items']:
            table = Table(title="Itens Gerados")
            table.add_column("Tipo", style="cyan")
            table.add_column("Origem", style="green")
            table.add_column("Destino", style="green")
            table.add_column("Conteúdo")
            
            for item in run['items']:
                table.add_row(
                    item['item_type'],
                    item['source_agent'] or "N/A",
                    item['target_agent'] or "N/A",
                    Text(format_json(item['raw_item'])[:100] + "...")
                )
            
            console.print("\n")
            console.print(table)
        
        # Guardrails
        if run['guardrails']:
            table = Table(title="Resultados de Guardrails")
            table.add_column("Tipo", style="cyan")
            table.add_column("Resultados")
            
            for guard in run['guardrails']:
                table.add_row(
                    guard['guardrail_type'],
                    Text(format_json(guard['results'])[:100] + "...")
                )
            
            console.print("\n")
            console.print(table)
        
        # Respostas brutas
        if run['raw_responses']:
            table = Table(title="Respostas Brutas do LLM")
            table.add_column("ID", style="dim")
            table.add_column("Resposta")
            
            for resp in run['raw_responses']:
                table.add_row(
                    str(resp['id']),
                    Text(format_json(resp['response'])[:100] + "...")
                )
            
            console.print("\n")
            console.print(table)

    def show_run_list(runs: List[Dict[str, Any]]):
        """Mostra lista resumida de execuções."""
        table = Table(title="Histórico de Execuções")
        table.add_column("ID", style="dim")
        table.add_column("Timestamp", style="cyan")
        table.add_column("Session", style="green")
        table.add_column("Agente", style="blue")
        table.add_column("Items", justify="right")
        table.add_column("Guards", justify="right")
        table.add_column("Resps", justify="right")
        
        for run in runs:
            table.add_row(
                str(run['id']),
                format_timestamp(run['timestamp']),
                run['session_id'][:8] + "...",
                run['last_agent'] or "N/A",
                str(len(run['items'])),
                str(len(run['guardrails'])),
                str(len(run['raw_responses']))
            )
        
        console.print(table)
