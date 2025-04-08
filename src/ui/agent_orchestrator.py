#!/usr/bin/env python3
"""
Orquestrador de Agentes - Interface TUI para execução de prompts e visualização de resultados.
"""

import logging
import json
import os
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Button, Footer, Header, Input, Static, RadioSet, RadioButton
from textual import on
from textual.binding import Binding
from textual.css.query import NoMatches

from src.core.models import ModelManager

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
        Binding("meta+q", "quit", "Sair"),
    ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Inicializa o ModelManager para obter a lista de modelos disponíveis
        self.model_manager = ModelManager()
        self.available_models = self._get_available_models()
    
    def _get_available_models(self):
        """Obtém a lista de modelos disponíveis no sistema."""
        modelos = []
        
        # Modelos locais
        modelos.append("tinyllama-1.1b")
        modelos.append("phi-1")
        modelos.append("deepseek-coder-6.7b")
        modelos.append("phi3-mini")
        
        # Modelos remotos (sempre incluídos como opções)
        modelos.append("gpt-3.5-turbo")
        modelos.append("gpt-4")
        modelos.append("gemini-pro")
        modelos.append("claude-3-opus")
        
        return modelos
    
    def compose(self) -> ComposeResult:
        """Compõe a interface principal."""
        yield Header()
        yield Footer()
        
        with Container(id="gen-panel"):
            yield Input(placeholder="Digite seu prompt aqui...", id="prompt-input")
            
            with Container(id="options-container"):
                # Seleção de formato de saída
                with Container(id="format-container"):
                    yield Static("Formato de saída:", id="format-label")
                    with RadioSet(id="format-select"):
                        yield RadioButton("JSON", value=True)
                        yield RadioButton("Markdown")
                
                # Seleção de modelo
                with Container(id="model-container"):
                    yield Static("Modelo:", id="model-label")
                    with RadioSet(id="model-select"):
                        for i, modelo in enumerate(self.available_models):
                            yield RadioButton(modelo, value=(i == 0))  # Seleciona o primeiro por padrão
                
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
        
        # Obtém o formato selecionado
        formato = "json" if self.query_one("#format-select").pressed_button.label == "JSON" else "markdown"
        
        # Obtém o modelo selecionado
        modelo = str(self.query_one("#model-select").pressed_button.label)
        
        # Atualiza o modelo no ModelManager (apenas simulação nesta fase)
        # self.model_manager.configure(model=modelo)
        
        # Simulação de resposta
        if formato == "json":
            conteudo = {
                "prompt": prompt,
                "modelo": modelo,
                "resposta": "Esta é uma resposta simulada em JSON",
                "timestamp": "2023-06-15 10:30:00"
            }
            resultado = f"[bold green]Resposta JSON:[/]\n\n[yellow]{json.dumps(conteudo, indent=2)}[/]"
        else:
            resultado = f"[bold green]Resposta Markdown:[/]\n\n[yellow]# Resposta para: {prompt}\n\n## Usando modelo: {modelo}\n\nEsta é uma resposta simulada em Markdown.[/]"
        
        self.query_one("#output", Static).update(resultado)
        self.notify(f"Conteúdo gerado com sucesso usando {modelo} em formato {formato.upper()}!", severity="success")

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