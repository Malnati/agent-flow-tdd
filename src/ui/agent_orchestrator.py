"""
src/ui/agent_orchestrator.py
Interface gráfica para o orquestrador de agentes.
"""

from textual.app import App, ComposeResult
from textual.containers import Vertical, Container
from textual.widgets import Header, Footer, Tabs, Tab, Input, OptionList, Pretty, Static
from textual.reactive import reactive
from textual.events import Key
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Footer, Header, Input, Static
from textual import on
from textual.css.query import NoMatches
from textual.reactive import reactive

from src.core.models import ModelManager
from src.core.agents import AgentOrchestrator
from src.core.db import DatabaseManager
from src.core.logger import get_logger
from src.core.models import ModelRegistry

# Obter caminho da raiz do projeto
BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"

# Garantir que os diretórios existem
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Configuração de logging
logger = get_logger(__name__)

class PromptGenTab(Vertical):
    """Aba de geração de prompts."""
    
    def compose(self) -> ComposeResult:
        # Inicializamos um ModelManager temporário para obter a lista de modelos disponíveis
        modelos = []
        try:
            manager = ModelManager()
            # Extraímos todos os modelos de todas as categorias em uma lista plana
            for categoria_modelos in manager.get_available_models().values():
                modelos.extend(categoria_modelos)
            logger.info(f"Modelos disponíveis para o PromptGenTab: {len(modelos)}")
        except Exception as e:
            logger.error(f"Erro ao obter modelos disponíveis: {str(e)}", exc_info=True)
            # Propaga a exceção para ser tratada pela aplicação principal
            raise
        
        yield Static("Digite o prompt abaixo:")
        yield Input(placeholder="Digite seu prompt...", id="prompt_input")
        yield Static("Selecione o modelo:")
        yield OptionList(*modelos, id="model_list")
        yield Static("Modelo de fallback (opcional):")
        yield OptionList(*modelos, id="fallback_model_list")
        yield Static("Modelo de elevação (opcional):")
        yield OptionList(*modelos, id="elevation_model_list")
        yield Static("Resultado da geração:")
        yield Pretty({}, id="result_output")
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Trata o evento quando o ENTER é pressionado no campo de prompt."""
        if event.input.id == "prompt_input":
            # Propagamos o evento para a aplicação principal
            self.app.on_input_submitted(event)


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
        ("s", "quit", "Sair do app"),
        ("enter", "gerar_conteudo", "Gerar conteúdo"),
    ]
    
    selected_tab = reactive("Gen")

    def _get_orchestrator(self, modelo: str = None) -> AgentOrchestrator:
        """
        Inicializa e retorna um AgentOrchestrator com os modelos selecionados.
        
        Args:
            modelo: Nome do modelo principal (opcional)
            
        Returns:
            Uma instância de AgentOrchestrator configurada
        """
        try:
            # Obtém modelo principal
            selected_model = modelo or self.tui.prompt_gen_tab.model_list.selected
            logger.debug(f"Modelo selecionado: {selected_model}")
            
            # Obtém modelo de fallback (se selecionado)
            fallback_model = None
            if hasattr(self.tui.prompt_gen_tab, 'fallback_model_list') and \
               self.tui.prompt_gen_tab.fallback_model_list:
                fallback_model = self.tui.prompt_gen_tab.fallback_model_list.selected
                logger.debug(f"Modelo de fallback selecionado: {fallback_model}")
            
            # Obtém modelo de elevação (se selecionado)
            elevation_model = None
            if hasattr(self.tui.prompt_gen_tab, 'elevation_model_list') and \
               self.tui.prompt_gen_tab.elevation_model_list:
                elevation_model = self.tui.prompt_gen_tab.elevation_model_list.selected
                logger.debug(f"Modelo de elevação selecionado: {elevation_model}")
            
            # Inicializa o gerenciador de modelos com os modelos selecionados
            model_manager = ModelManager(
                model_name=selected_model,
                fallback_model=fallback_model,
                elevation_model=elevation_model
            )
            
            # Inicializa o gerenciador de banco de dados para logging de execuções
            db_manager = DatabaseManager()
            
            return AgentOrchestrator(
                model_manager=model_manager,
                db_manager=db_manager
            )
        except Exception as e:
            logger.error(f"Erro ao inicializar orchestrator: {str(e)}")
            raise
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Tabs(Tab("Gen", id="Gen"), id="tabs")
        yield Container(id="content_container")
        yield Footer()

    def on_mount(self) -> None:
        # Inicializa o ModelManager para obter a lista de modelos disponíveis
        try:
            self.model_manager = ModelManager()
            # Obtemos todos os modelos disponíveis dinamicamente
            models_by_provider = self.model_manager.get_available_models()
            # Criamos uma lista plana com todos os modelos de todas as categorias
            self.available_models = [
                modelo for modelos in models_by_provider.values() for modelo in modelos
            ]
            logger.info(f"Modelos disponíveis: {self.available_models}")
        except Exception as e:
            logger.error(f"Erro ao inicializar ModelManager: {str(e)}", exc_info=True)
            self.notify(f"Erro ao inicializar: {str(e)}", severity="error")
            
        # Inicializa o DatabaseManager para registrar execuções
        try:
            self.db = DatabaseManager(db_path=str(DATA_DIR / "agent_logs.db"))
        except Exception as e:
            logger.error(f"Erro ao inicializar DatabaseManager: {str(e)}", exc_info=True)
            self.notify(f"Erro ao inicializar banco de dados: {str(e)}", severity="error")
            
        # Inicializa o orquestrador
        self.orchestrator = None
        # ID de sessão para registrar logs
        self.session_id = f"tui_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        self.query_one("#tabs", Tabs).active = "Gen"
        self.mount_tab("Gen")
        
        logger.info("Aplicativo iniciado com sucesso")

    def mount_tab(self, tab_name: str):
        container = self.query_one("#content_container", Container)
        container.remove_children()

        if tab_name == "Gen":
            container.mount(PromptGenTab())

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        self.selected_tab = event.tab.id
        self.mount_tab(self.selected_tab)

    @on(Input.Submitted)
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Ação quando o ENTER é pressionado em um campo de input."""
        logger.info(f"Input submetido: {event.input.id}")
        
        # Gera conteúdo independentemente do input onde ENTER foi pressionado
        self.gerar_conteudo()
        
    @on(Key)
    def on_key(self, event: Key) -> None:
        """Captura eventos de tecla."""
        if event.key == "enter":
            # Evita duplicação quando o evento já estiver sendo tratado por um input de prompt
            # mas permite para outros inputs como o seletor de modelos
            if not isinstance(self.screen.focused, Input) or self.screen.focused.id != "prompt_input":
                logger.info("Tecla ENTER pressionada, gerando conteúdo...")
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
                if option_list.highlighted is not None:
                    modelo = self.available_models[option_list.highlighted]
                else:
                    modelo = self.available_models[0] if self.available_models else "gpt-3.5-turbo"  # Modelo padrão
                    self.notify("Nenhum modelo selecionado, usando modelo padrão", severity="warning")
            except NoMatches:
                modelo = self.available_models[0] if self.available_models else "gpt-3.5-turbo"  # Modelo padrão
                self.notify("Lista de modelos não encontrada, usando modelo padrão", severity="warning")
                
            logger.info(f"Prompt submetido, gerando conteúdo...")
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
            logger.error(f"Erro ao executar orquestrador: {error_msg}", exc_info=True)
            try:
                self.query_one("#result_output", Pretty).update({"erro": error_msg})
            except NoMatches:
                logger.error("Componente de saída não encontrado")
            self.notify(f"Erro ao gerar conteúdo: {error_msg}", severity="error")

    def action_gerar_conteudo(self) -> None:
        """Ação chamada quando a tecla 'enter' é pressionada."""
        logger.info("Ação gerar_conteudo acionada via binding")
        self.gerar_conteudo()

    def action_quit(self) -> None:
        """Ação para sair do aplicativo."""
        logger.info("Finalizando aplicação via ação quit")
        self.exit()

if __name__ == "__main__":
    logger.info("INÍCIO - main | Iniciando Orquestrador Simples")
    app = TDDPromptApp()
    app.run()
    logger.info("FIM - main | Aplicativo finalizado")