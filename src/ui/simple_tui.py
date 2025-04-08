#!/usr/bin/env python3
"""
Aplicativo TUI mínimo para demonstrar o Textual.
"""

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button, Input
from textual.containers import Container
from textual import on

class SimpleTUI(App):
    """Aplicativo TUI mínimo."""
    
    TITLE = "Aplicativo TUI Simples"
    
    def compose(self) -> ComposeResult:
        """Compõe a interface principal."""
        yield Header()
        yield Container(
            Input(placeholder="Digite seu prompt aqui..."),
            Button("Executar", id="execute-button"),
            Static("Resultado aparecerá aqui", id="output"),
            id="main",
        )
        yield Footer()
    
    @on(Button.Pressed, "#execute-button")
    def on_button_pressed(self) -> None:
        """Ação quando o botão é pressionado."""
        input_text = self.query_one(Input).value
        if input_text:
            self.query_one("#output", Static).update(f"Você digitou: {input_text}")
        else:
            self.query_one("#output", Static).update("Por favor, digite algo primeiro.")

def main():
    """Função principal para executar o aplicativo."""
    app = SimpleTUI()
    app.run()

if __name__ == "__main__":
    main() 