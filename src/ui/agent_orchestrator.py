#!/usr/bin/env python3
"""
Orquestrador de Agentes - Interface TUI para execução de prompts e visualização de resultados.
"""

import logging
import json
import os
import uuid
from datetime import datetime
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Button, Footer, Header, Input, Static, RadioSet, RadioButton
from textual import on
from textual.binding import Binding
from textual.css.query import NoMatches

from src.core.models import ModelManager
from src.core.agents import AgentOrchestrator
from src.core.db import DatabaseManager

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
        # Múltiplas alternativas para sair do aplicativo
        Binding("ctrl+meta+q", "quit", "Sair"),
        Binding("ctrl+q", "quit", "Sair"),
        Binding("meta+q", "quit", "Sair"),
        Binding("q", "quit", "Sair"),
    ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Inicializa o ModelManager para obter a lista de modelos disponíveis
        self.model_manager = ModelManager()
        self.available_models = self._get_available_models()
        # Inicializa o DatabaseManager para registrar execuções
        self.db = DatabaseManager()
        # Inicializa o orquestrador
        self.orchestrator = None
        # ID de sessão para registrar logs
        self.session_id = f"tui_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    def _get_available_models(self):
        """Obtém a lista de modelos disponíveis no sistema."""
        modelos = []
        
        # Modelos locais
        modelos.append("tinyllama-1.1b")
        modelos.append("phi-1")
        modelos.append("deepseek-coder-6.7b")  # Nome correto para o modelo DeepSeek
        modelos.append("phi3-mini")  # Nome correto para o modelo Phi-3
        
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
    
    def _get_orchestrator(self, modelo):
        """
        Obtém uma instância do orquestrador de agentes com o modelo selecionado.
        
        Args:
            modelo: Nome do modelo a ser usado
            
        Returns:
            AgentOrchestrator configurado
        """
        try:
            # Configura o modelo via variável de ambiente
            os.environ["DEFAULT_MODEL"] = modelo
            
            # Inicializa componentes
            model_manager = ModelManager(model_name=modelo)
            
            # Verifica disponibilidade do modelo local selecionado
            # Se for tinyllama e não estiver disponível, usa fallback
            if modelo.startswith("tinyllama-") and not model_manager.tinyllama_model:
                logger.warning("Modelo TinyLlama não disponível. Usando modelo alternativo.")
                self.notify("Modelo TinyLlama não disponível, usando modelo alternativo.", severity="warning")
                os.environ["DEFAULT_MODEL"] = "gpt-3.5-turbo"
                model_manager = ModelManager(model_name="gpt-3.5-turbo")
            
            # Se for phi-1 e não estiver disponível, usa fallback
            elif modelo == "phi-1" and not model_manager.phi1_model:
                logger.warning("Modelo Phi-1 não disponível. Usando modelo alternativo.")
                self.notify("Modelo Phi-1 não disponível, usando modelo alternativo.", severity="warning")
                os.environ["DEFAULT_MODEL"] = "gpt-3.5-turbo"
                model_manager = ModelManager(model_name="gpt-3.5-turbo")
            
            # Se for deepseek e não estiver disponível, usa fallback
            elif modelo == "deepseek-coder-6.7b" and not model_manager.deepseek_model:
                logger.warning("Modelo DeepSeek não disponível. Usando modelo alternativo.")
                self.notify("Modelo DeepSeek não disponível, usando modelo alternativo.", severity="warning")
                os.environ["DEFAULT_MODEL"] = "gpt-3.5-turbo"
                model_manager = ModelManager(model_name="gpt-3.5-turbo")
            
            # Se for phi3 e não estiver disponível, usa fallback
            elif modelo == "phi3-mini" and not model_manager.phi3_model:
                logger.warning("Modelo Phi-3 Mini não disponível. Usando modelo alternativo.")
                self.notify("Modelo Phi-3 Mini não disponível, usando modelo alternativo.", severity="warning")
                os.environ["DEFAULT_MODEL"] = "gpt-3.5-turbo"
                model_manager = ModelManager(model_name="gpt-3.5-turbo")
                
            # Inicializa o DatabaseManager
            db = DatabaseManager()
            
            # Cria o orquestrador com o modelo selecionado
            orchestrator = AgentOrchestrator(model_manager.model_name)
            
            # Atribui o model_manager como atributo
            orchestrator.model_manager = model_manager
            
            # Define o db como atributo separado
            orchestrator.db = db
            
            logger.info(f"Orquestrador inicializado com modelo {model_manager.model_name}")
            return orchestrator
            
        except Exception as e:
            logger.error(f"Erro ao criar orquestrador: {str(e)}")
            self.notify(f"Erro ao inicializar o modelo: {str(e)}", severity="error")
            raise
    
    def gerar_conteudo(self) -> None:
        """Gera conteúdo com base no prompt usando o orquestrador de agentes."""
        self.notify("Gerando conteúdo...")
        prompt = self.query_one("#prompt-input", Input).value
        
        if not prompt:
            self.notify("Por favor, digite um prompt", severity="error")
            return
        
        # Obtém o formato selecionado
        formato = "json" if self.query_one("#format-select").pressed_button.label == "JSON" else "markdown"
        
        # Obtém o modelo selecionado
        modelo = str(self.query_one("#model-select").pressed_button.label)
        
        try:
            # Inicializa o orquestrador com o modelo selecionado
            orchestrator = self._get_orchestrator(modelo)
            
            # Executa o orquestrador com o prompt e formato especificados
            result = orchestrator.execute(
                prompt=prompt,
                format=formato
            )
            
            # Formata a saída de acordo com o formato especificado
            if formato == "json":
                try:
                    # Tenta converter para um objeto Python se a resposta for um JSON como string
                    output_content = json.loads(result.output) if isinstance(result.output, str) else result.output
                    resultado = f"[bold green]Resposta JSON:[/]\n\n[yellow]{json.dumps(output_content, indent=2, ensure_ascii=False)}[/]"
                except (json.JSONDecodeError, TypeError):
                    # Se não for um JSON válido, mostra como texto
                    resultado = f"[bold green]Resposta:[/]\n\n[yellow]{result.output}[/]"
            else:
                resultado = f"[bold green]Resposta Markdown:[/]\n\n[yellow]{result.output}[/]"
            
            # Atualiza a interface com o resultado
            self.query_one("#output", Static).update(resultado)
            self.notify(f"Conteúdo gerado com sucesso usando {modelo} em formato {formato.upper()}!", severity="success")
            
            # Registra a execução no banco de dados
            self.db.log_run(
                self.session_id,
                input=prompt,
                final_output=result.output,
                output_type=formato
            )
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Erro ao executar orquestrador: {error_msg}")
            self.query_one("#output", Static).update(f"[bold red]Erro:[/]\n\n{error_msg}")
            self.notify(f"Erro ao gerar conteúdo: {error_msg}", severity="error")

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