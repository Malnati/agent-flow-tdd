#!/usr/bin/env python3
"""
Orquestrador de Agentes - Interface TUI para execução de prompts e visualização de resultados.
"""

import logging
import json
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Button, Footer, Header, Input, Static
from textual import on
from textual.binding import Binding
from textual.css.query import NoMatches

# Configuração de logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

class SimpleOrchestratorApp(App):
    """Aplicativo simples para orquestrar prompts."""
    
    TITLE = "Orquestrador de Prompts"
    # CSS_PATH = "agent_orchestrator.tcss"
    
    BINDINGS = [
        Binding("ctrl+q", "quit", "Sair"),
    ]
    
    def compose(self) -> ComposeResult:
        """Compõe a interface principal."""
        yield Header()
        yield Footer()
        
        with Container(id="gen-panel"):
            yield Input(placeholder="Digite seu prompt aqui...", id="prompt-input")
            yield Button("Gerar", variant="success", id="gen-button")
            yield Static("[b]Aguardando entrada...[/b]", id="output")
    
    @on(Button.Pressed, "#gen-button")
    def on_button_pressed(self) -> None:
        """Ação quando o botão é pressionado."""
        self.gerar_conteudo()
    
    @on(Input.Submitted)
    def on_input_submitted(self) -> None:
        """Ação quando o ENTER é pressionado em um campo de input."""
        self.gerar_conteudo()
    
    def gerar_conteudo(self) -> None:
        """Gera conteúdo com base no prompt."""
        self.notify("Gerando conteúdo...")
        prompt = self.query_one("#prompt-input", Input).value
        
        if not prompt:
            self.notify("Por favor, digite um prompt", severity="error")
            return
        
        # Simulação de resposta
        resultado = f"[bold green]Resposta para:[/] [yellow]{prompt}[/]\n\n[white]Esta é uma resposta simulada.[/]"
        self.query_one("#output", Static).update(resultado)
        self.notify("Conteúdo gerado com sucesso!", severity="success")

    def on_mount(self) -> None:
        """Evento disparado quando o aplicativo é montado."""
        # Coloca o foco no campo de input automaticamente
        try:
            self.query_one("#prompt-input").focus()
        except NoMatches:
            pass

    def action_quit(self) -> None:
        """Ação para sair do aplicativo."""
        self.exit()

def main():
    """Função principal para executar o aplicativo."""
    try:
        logger.info("INÍCIO - main | Iniciando Orquestrador Simples")
        app = SimpleOrchestratorApp()
        app.run()
        logger.info("FIM - main | Aplicativo finalizado")
    except Exception as e:
        logger.error(f"FALHA - main | Erro ao executar aplicativo: {str(e)}", exc_info=True)
        print(f"Erro ao executar aplicativo: {str(e)}")

if __name__ == "__main__":
    main() 