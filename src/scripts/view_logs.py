"""
Script para visualização dos logs do banco de dados.
"""
import argparse
import json
from datetime import datetime
from typing import Dict, Any, List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from src.core.db import DatabaseManager

console = Console()

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

def show_run_details(run: Dict[str, Any]) -> None:
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

def show_run_list(runs: List[Dict[str, Any]]) -> None:
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

def main():
    """Função principal."""
    parser = argparse.ArgumentParser(description="Visualizador de logs do Agent Flow TDD")
    parser.add_argument("--limit", type=int, default=10, help="Número máximo de registros")
    parser.add_argument("--session", type=str, help="Filtrar por session ID")
    parser.add_argument("--agent", type=str, help="Filtrar por agente")
    parser.add_argument("--id", type=int, help="Mostrar detalhes de uma execução específica")
    args = parser.parse_args()
    
    try:
        db = DatabaseManager()
        runs = db.get_run_history(limit=args.limit)
        
        # Filtra resultados se necessário
        if args.session:
            runs = [r for r in runs if args.session in r['session_id']]
        if args.agent:
            runs = [r for r in runs if r['last_agent'] and args.agent in r['last_agent']]
        
        # Mostra detalhes de uma execução específica
        if args.id:
            for run in runs:
                if run['id'] == args.id:
                    show_run_details(run)
                    break
            else:
                console.print(f"[red]Execução {args.id} não encontrada![/red]")
        
        # Ou mostra lista resumida
        else:
            show_run_list(runs)
        
    except Exception as e:
        console.print(f"[red]Erro ao acessar logs: {str(e)}[/red]")
    finally:
        db.close()

if __name__ == "__main__":
    main() 