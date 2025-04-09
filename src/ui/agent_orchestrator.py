from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import Header, Footer, Tabs, Tab, Input, OptionList, Pretty, Static
from textual.reactive import reactive
from textual.events import Key
import logging
import json
import os
import uuid
from datetime import datetime
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Footer, Header, Input, Static, RadioSet, RadioButton
from textual import on
from textual.binding import Binding
from textual.css.query import NoMatches
from textual.reactive import reactive

from src.core.models import ModelManager
from src.core.agents import AgentOrchestrator
from src.core.db import DatabaseManager

# Modelos disponíveis para seleção
MODEL_OPTIONS = [
    "tinyllama-1.1b",
    "phi-1",
    "deepseek-coder-6.7b",
    "phi-3-mini",
    "gpt-4",
    "claude-3-opus"
]

# Configuração de logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="logs/agent_orchestrator.log"
)

class PromptGenTab(Vertical):
    def compose(self) -> ComposeResult:
        yield Static("Digite o prompt abaixo:")
        yield Input(placeholder="Digite seu prompt...", id="prompt_input")
        yield Static("Selecione o modelo:")
        yield OptionList(*MODEL_OPTIONS, id="model_list")
        yield Static("Resultado da geração:")
        yield Pretty({}, id="result_output")


class TDDPromptApp(App):
    CSS = """
    #content_container {
        height: 1fr;
        padding: 1;
    }
    
    OptionList {
        height: auto;
        max-height: 10;
        border: solid $accent;
    }
    
    Pretty {
        height: auto;
        max-height: 1fr;
        border: solid $primary;
        overflow: auto;
    }
    
    Input {
        margin: 1 0;
    }
    
    Static {
        margin-top: 1;
    }
    """
    
    BINDINGS = [
        ("s", "quit", "Sair do app")
    ]
    
    selected_tab = reactive("Gen")

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
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Tabs(Tab("Gen", id="Gen"), id="tabs")
        yield Container(id="content_container")
        yield Footer()

    def on_mount(self) -> None:
        # Inicializa o ModelManager para obter a lista de modelos disponíveis
        self.model_manager = ModelManager()
        self.available_models = self._get_available_models()
        # Inicializa o DatabaseManager para registrar execuções
        self.db = DatabaseManager()
        # Inicializa o orquestrador
        self.orchestrator = None
        # ID de sessão para registrar logs
        self.session_id = f"tui_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        self.query_one("#tabs", Tabs).active = "Gen"
        self.mount_tab("Gen")

    def mount_tab(self, tab_name: str):
        container = self.query_one("#content_container", Container)
        container.remove_children()

        if tab_name == "Gen":
            container.mount(PromptGenTab())

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        self.selected_tab = event.tab.id
        self.mount_tab(self.selected_tab)

    @on(Input.Submitted)
    def on_input_submitted(self) -> None:
        """Ação quando o ENTER é pressionado em um campo de input."""
        self.gerar_conteudo()

    def gerar_conteudo(self) -> None:
        """Gera conteúdo com base no prompt usando o orquestrador de agentes."""
        self.notify("Gerando conteúdo...")
        try:
            # Obtém o valor do prompt do campo de input
            prompt = self.query_one("#prompt_input", Input).value
            
            if not prompt:
                self.notify("Por favor, digite um prompt", severity="error")
                return
            
            # Define valores padrão para formato e modelo
            formato = "json"  # Padrão: JSON
            
            # Obtém o modelo selecionado na lista
            try:
                option_list = self.query_one("#model_list", OptionList)
                if option_list.selected is not None:
                    modelo = MODEL_OPTIONS[option_list.selected]
                else:
                    modelo = "gpt-3.5-turbo"  # Modelo padrão
                    self.notify("Nenhum modelo selecionado, usando modelo padrão", severity="warning")
            except NoMatches:
                modelo = "gpt-3.5-turbo"  # Modelo padrão
                self.notify("Lista de modelos não encontrada, usando modelo padrão", severity="warning")
                
            logger.info(f"Gerando conteúdo com modelo: {modelo}")
            
            # Inicializa o orquestrador com o modelo selecionado
            orchestrator = self._get_orchestrator(modelo)
            
            # Executa o orquestrador com o prompt e formato especificados
            result = orchestrator.execute(
                prompt=prompt,
                format=formato
            )
            
            try:
                # Tenta converter para um objeto Python se a resposta for um JSON como string
                output_content = json.loads(result.output) if isinstance(result.output, str) else result.output
                resultado = output_content
            except (json.JSONDecodeError, TypeError):
                # Se não for um JSON válido, mostra como texto
                resultado = result.output
            
            # Atualiza a interface com o resultado
            self.query_one("#result_output", Pretty).update(resultado)
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
            try:
                self.query_one("#result_output", Pretty).update({"erro": error_msg})
            except NoMatches:
                logger.error("Componente de saída não encontrado")
            self.notify(f"Erro ao gerar conteúdo: {error_msg}", severity="error")

if __name__ == "__main__":
    logger.info("INÍCIO - main | Iniciando Orquestrador Simples")
    app = TDDPromptApp()
    app.run()
    logger.info("FIM - main | Aplicativo finalizado")