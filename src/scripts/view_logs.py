"""
Script para visualização dos logs do banco de dados.
"""
import argparse

from rich.console import Console

from src.core.db import DatabaseManager

console = Console()

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
                    db.show_run_details(run)
                    break
            else:
                console.print(f"[red]Execução {args.id} não encontrada![/red]")
        
        # Ou mostra lista resumida
        else:
            db.show_run_list(runs)
        
    except Exception as e:
        console.print(f"[red]Erro ao acessar logs: {str(e)}[/red]")
    finally:
        db.close()

if __name__ == "__main__":
    main() 