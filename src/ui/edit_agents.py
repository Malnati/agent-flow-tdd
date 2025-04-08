#!/usr/bin/env python3
"""
Editor de prompts para o arquivo de configuração de agentes.
Permite visualizar, adicionar, editar e remover prompts do arquivo JSON.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Button, 
    Footer, 
    Header, 
    Input, 
    Label, 
    RadioSet, 
    RadioButton,
    Tree, 
    TextArea
)
from textual.widgets.tree import TreeNode
from textual.screen import Screen
from textual.binding import Binding

# Configuração de logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

# Caminho para o arquivo JSON
AGENTS_JSON_PATH = Path(__file__).parent.parent / "configs" / "agents.json"


class ConfirmDeleteScreen(Screen):
    """Tela de confirmação para deletar um prompt."""

    BINDINGS = [
        Binding("y", "confirm", "Confirmar"),
        Binding("n", "cancel", "Cancelar"),
        Binding("escape", "cancel", "Cancelar"),
    ]

    def __init__(self, path: List[str]):
        """Inicializa a tela de confirmação.
        
        Args:
            path: Caminho do prompt a ser removido no JSON.
        """
        super().__init__()
        self.path = path

    def compose(self) -> ComposeResult:
        """Compõe a tela de confirmação."""
        with Container(id="confirm-dialog"):
            path_str = " > ".join(self.path)
            yield Label(f"Tem certeza que deseja excluir: {path_str}?")
            with Horizontal(id="confirm-buttons"):
                yield Button("Sim (Y)", variant="error", id="yes")
                yield Button("Não (N)", variant="primary", id="no")

    def action_confirm(self) -> None:
        """Confirma a exclusão."""
        self.dismiss(True)

    def action_cancel(self) -> None:
        """Cancela a exclusão."""
        self.dismiss(False)
    
    @on(Button.Pressed, "#yes")
    def on_yes_pressed(self) -> None:
        """Ação quando o botão 'Sim' é pressionado."""
        self.action_confirm()
    
    @on(Button.Pressed, "#no")
    def on_no_pressed(self) -> None:
        """Ação quando o botão 'Não' é pressionado."""
        self.action_cancel()


class EditPromptScreen(Screen):
    """Tela para edição de um prompt."""

    BINDINGS = [
        Binding("escape", "cancel", "Voltar"),
        Binding("ctrl+s", "save", "Salvar"),
    ]

    def __init__(
        self, 
        path: List[str], 
        data: Dict[str, Any], 
        is_new: bool = False,
        key_name: str = None
    ):
        """Inicializa a tela de edição.
        
        Args:
            path: Caminho do prompt no JSON.
            data: Dados atuais do prompt.
            is_new: Se é um novo prompt sendo criado.
            key_name: Nome da chave para um novo prompt.
        """
        super().__init__()
        self.path = path
        self.data = data
        self.is_new = is_new
        self.key_name = key_name
        self.editor_inputs = {}
        self.current_field = None

    def compose(self) -> ComposeResult:
        """Compõe a tela de edição."""
        if not self.is_new:
            title = " > ".join(self.path)
        else:
            parent_path = " > ".join(self.path)
            title = f"Novo prompt em {parent_path}"
        
        yield Header(title)
        yield Footer()

        with Container(id="edit-form"):
            # Se for um novo prompt, primeiro solicitar o nome da chave
            if self.is_new and not self.key_name:
                yield Label("Nome da chave:")
                yield Input(id="key-name")
                yield Button("Continuar", id="continue-button")
            else:
                # Exibir campos para edição
                if isinstance(self.data, dict):
                    for key, value in self.data.items():
                        with Vertical(classes="form-field"):
                            yield Label(f"{key}:")
                            if isinstance(value, dict):
                                # Para dicionários aninhados, exibimos como JSON formatado
                                text_area = TextArea(json.dumps(value, indent=4), id=f"field-{key}")
                                yield text_area
                                self.editor_inputs[key] = text_area
                            else:
                                # Para strings ou outros valores simples
                                if isinstance(value, str):
                                    text_area = TextArea(value, id=f"field-{key}")
                                else:
                                    text_area = TextArea(str(value), id=f"field-{key}")
                                yield text_area
                                self.editor_inputs[key] = text_area
                else:
                    # Para valores não dicionários (strings, etc.)
                    text_area = TextArea(str(self.data) if self.data is not None else "", id="field-value")
                    yield text_area
                    self.editor_inputs["value"] = text_area
                
                with Horizontal(id="edit-buttons"):
                    yield Button("Salvar (Ctrl+S)", variant="primary", id="save-button")
                    yield Button("Cancelar (Esc)", variant="default", id="cancel-button")

    def action_save(self) -> None:
        """Salva as alterações e retorna à tela principal."""
        if self.is_new and not self.key_name:
            key_input = self.query_one("#key-name", Input)
            self.key_name = key_input.value.strip()
            if not self.key_name:
                self.notify("O nome da chave não pode estar vazio", severity="error")
                return
            # Recarrega a tela com o nome da chave definido
            self.app.pop_screen()
            self.app.push_screen(EditPromptScreen(self.path, {}, self.is_new, self.key_name))
            return
        
        updated_data = {}
        try:
            # Para cada campo de entrada, recuperamos o valor atual
            for key, editor in self.editor_inputs.items():
                value = editor.text
                
                # Tenta converter texto JSON para dicionário se for apropriado
                if key in self.data and isinstance(self.data[key], dict):
                    try:
                        updated_data[key] = json.loads(value)
                    except json.JSONDecodeError:
                        self.notify(f"Erro no formato JSON do campo {key}", severity="error")
                        return
                else:
                    updated_data[key] = value
            
            # Retorna os dados atualizados e outras informações
            result = {
                "path": self.path,
                "data": updated_data,
                "is_new": self.is_new,
                "key_name": self.key_name
            }
            self.dismiss(result)
        except Exception as e:
            logger.error(f"Erro ao processar dados do formulário: {str(e)}")
            self.notify(f"Erro ao processar dados: {str(e)}", severity="error")

    def action_cancel(self) -> None:
        """Cancela a edição e retorna à tela principal."""
        self.dismiss(None)
    
    @on(Button.Pressed, "#save-button")
    def on_save_pressed(self) -> None:
        """Ação quando o botão 'Salvar' é pressionado."""
        self.action_save()
    
    @on(Button.Pressed, "#cancel-button")
    def on_cancel_pressed(self) -> None:
        """Ação quando o botão 'Cancelar' é pressionado."""
        self.action_cancel()
    
    @on(Button.Pressed, "#continue-button")
    def on_continue_pressed(self) -> None:
        """Ação quando o botão 'Continuar' é pressionado."""
        self.action_save()


class PromptsEditorApp(App):
    """Aplicativo principal para edição de prompts."""

    TITLE = "Editor de Prompts"
    CSS = """
    #tree-panel {
        width: 30%;
        min-width: 30;
        height: 100%;
        border-right: solid $primary;
    }
    
    #detail-panel {
        width: 70%;
        height: 100%;
        padding: 1 2;
    }
    
    #section-selector {
        margin-bottom: 1;
    }
    
    #detail-content {
        height: 100%;
        overflow: auto;
    }
    
    #confirm-dialog {
        background: $surface;
        border: solid $primary;
        padding: 1 2;
        width: 60%;
        height: auto;
        margin: 2 2 2 2;
    }
    
    #confirm-buttons {
        margin-top: 1;
        width: 100%;
        align: center middle;
    }
    
    #edit-form {
        padding: 1;
        height: 100%;
        overflow: auto;
    }
    
    .form-field {
        margin-bottom: 1;
    }
    
    #edit-buttons {
        margin-top: 2;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Sair"),
        Binding("s", "save_data", "Salvar"),
        Binding("a", "add_prompt", "Adicionar"),
        Binding("d", "delete_prompt", "Excluir"),
        Binding("e", "edit_prompt", "Editar"),
        Binding("r", "reload_data", "Recarregar"),
    ]

    def __init__(self):
        """Inicializa o aplicativo."""
        super().__init__()
        self.json_data = {}
        self.current_section = "GuardRails.Input"
        self.selected_node = None

    def on_mount(self) -> None:
        """Ação ao montar o aplicativo."""
        self.load_data()
        self.populate_tree()
    
    def compose(self) -> ComposeResult:
        """Compõe a interface principal."""
        yield Header()
        yield Footer()
        
        with Horizontal():
            with Vertical(id="tree-panel"):
                with RadioSet(id="section-selector"):
                    yield RadioButton("GuardRails.Input", value=True)
                    yield RadioButton("GuardRails.Output")
                    yield RadioButton("prompts")
                yield Tree("Prompts", id="prompts-tree")
            
            with Vertical(id="detail-panel"):
                yield Container(id="detail-content")
    
    def load_data(self) -> None:
        """Carrega os dados do arquivo JSON."""
        try:
            logger.info(f"INÍCIO - load_data | Carregando dados de {AGENTS_JSON_PATH}")
            with open(AGENTS_JSON_PATH, "r", encoding="utf-8") as file:
                self.json_data = json.load(file)
            logger.info("FIM - load_data | Dados carregados com sucesso")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"FALHA - load_data | Erro ao carregar arquivo JSON: {str(e)}")
            self.notify(f"Erro ao carregar arquivo: {str(e)}", severity="error")
            self.json_data = {}
    
    def save_data(self) -> None:
        """Salva os dados no arquivo JSON."""
        try:
            logger.info(f"INÍCIO - save_data | Salvando dados em {AGENTS_JSON_PATH}")
            with open(AGENTS_JSON_PATH, "w", encoding="utf-8") as file:
                json.dump(self.json_data, file, indent=4)
            self.notify("Arquivo salvo com sucesso", severity="information")
            logger.info("FIM - save_data | Dados salvos com sucesso")
        except Exception as e:
            logger.error(f"FALHA - save_data | Erro ao salvar arquivo: {str(e)}")
            self.notify(f"Erro ao salvar arquivo: {str(e)}", severity="error")
    
    def populate_tree(self) -> None:
        """Popula a árvore com os dados da seção atual."""
        try:
            logger.debug(f"INÍCIO - populate_tree | Seção: {self.current_section}")
            tree = self.query_one("#prompts-tree", Tree)
            tree.clear()
            
            # Parseamos a seção atual (pode ter subnível como GuardRails.Input)
            path_parts = self.current_section.split(".")
            current_data = self.json_data
            
            # Navega até o nível correto no JSON
            for part in path_parts:
                if part in current_data:
                    current_data = current_data[part]
                else:
                    current_data = {}
                    break
            
            # Adiciona nós para cada entrada na seção atual
            root = tree.root
            root.label = self.current_section
            
            if isinstance(current_data, dict):
                for key, value in current_data.items():
                    node = root.add(key)
                    node.data = {"path": path_parts + [key], "data": value}
            
            tree.root.expand()
            logger.debug("FIM - populate_tree")
        except Exception as e:
            logger.error(f"FALHA - populate_tree | Erro ao popular árvore: {str(e)}")
            self.notify(f"Erro ao exibir dados: {str(e)}", severity="error")
    
    def display_prompt(self, node: TreeNode) -> None:
        """Exibe os detalhes de um prompt selecionado.
        
        Args:
            node: Nó da árvore selecionado.
        """
        try:
            logger.debug(f"INÍCIO - display_prompt | Nó: {node.label}")
            detail_panel = self.query_one("#detail-content", Container)
            detail_panel.remove_children()
            
            if not hasattr(node, "data") or not node.data:
                return
            
            data = node.data["data"]
            
            if isinstance(data, dict):
                for key, value in data.items():
                    with Container(classes="field-container"):
                        detail_panel.mount(Label(f"{key}:", classes="field-label"))
                        
                        if isinstance(value, dict):
                            # Para dicionários, mostramos como JSON formatado
                            json_value = json.dumps(value, indent=2)
                            detail_panel.mount(TextArea(json_value, classes="field-value", read_only=True))
                        else:
                            # Para strings ou outros valores
                            detail_panel.mount(TextArea(str(value), classes="field-value", read_only=True))
            else:
                # Para valores que não são dicionários
                detail_panel.mount(TextArea(str(data), classes="field-value", read_only=True))
            
            logger.debug("FIM - display_prompt")
        except Exception as e:
            logger.error(f"FALHA - display_prompt | Erro ao exibir prompt: {str(e)}")
            self.notify(f"Erro ao exibir detalhes: {str(e)}", severity="error")
    
    def get_node_data_path(self, path_parts: List[str]) -> tuple:
        """Obtém o caminho para os dados a partir de uma lista de partes do caminho.
        
        Args:
            path_parts: Lista de partes do caminho no JSON.
            
        Returns:
            Tupla com (referência ao dicionário pai, última chave, dados atuais)
        """
        current = self.json_data
        parent = None
        last_key = None
        
        for i, part in enumerate(path_parts):
            if i == len(path_parts) - 1:
                parent = current
                last_key = part
            
            if part in current:
                current = current[part]
            else:
                return None, None, None
        
        return parent, last_key, current
    
    def update_data(self, path: List[str], updated_data: Dict[str, Any], is_new: bool = False, key_name: str = None) -> None:
        """Atualiza os dados no JSON com base no caminho fornecido.
        
        Args:
            path: Caminho para os dados a serem atualizados.
            updated_data: Novos dados.
            is_new: Se é um novo item sendo adicionado.
            key_name: Nome da chave para um novo item.
        """
        try:
            logger.info(f"INÍCIO - update_data | Caminho: {path}, É novo: {is_new}")
            
            if is_new:
                # Para um novo item, navegamos até o pai
                parent_path = path
                current = self.json_data
                
                # Navega até o nível parente
                for part in parent_path:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                
                # Adiciona o novo item
                current[key_name] = updated_data
                self.notify(f"Prompt '{key_name}' adicionado com sucesso", severity="information")
            else:
                # Para atualização, usamos o caminho completo
                parent, last_key, _ = self.get_node_data_path(path)
                
                if parent is not None and last_key is not None:
                    parent[last_key] = updated_data
                    self.notify("Prompt atualizado com sucesso", severity="information")
                else:
                    self.notify("Caminho não encontrado para atualização", severity="error")
                    return
            
            # Recarrega a árvore para refletir as mudanças
            self.populate_tree()
            logger.info("FIM - update_data | Dados atualizados com sucesso")
        except Exception as e:
            logger.error(f"FALHA - update_data | Erro ao atualizar dados: {str(e)}")
            self.notify(f"Erro ao atualizar dados: {str(e)}", severity="error")
    
    def delete_node(self, path: List[str]) -> None:
        """Remove um nó com base no caminho fornecido.
        
        Args:
            path: Caminho para o nó a ser removido.
        """
        try:
            logger.info(f"INÍCIO - delete_node | Caminho: {path}")
            parent, last_key, _ = self.get_node_data_path(path)
            
            if parent is not None and last_key is not None:
                del parent[last_key]
                self.notify(f"Prompt '{last_key}' removido com sucesso", severity="information")
                self.populate_tree()
            else:
                self.notify("Caminho não encontrado para remoção", severity="error")
            
            logger.info("FIM - delete_node | Nó removido com sucesso")
        except Exception as e:
            logger.error(f"FALHA - delete_node | Erro ao remover nó: {str(e)}")
            self.notify(f"Erro ao remover prompt: {str(e)}", severity="error")

    @on(Tree.NodeSelected)
    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Ação quando um nó é selecionado na árvore."""
        self.selected_node = event.node
        if hasattr(event.node, "data") and event.node.data:
            self.display_prompt(event.node)
    
    @on(RadioSet.Changed)
    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Ação quando a seleção de seção é alterada."""
        self.current_section = event.pressed.label
        self.populate_tree()
    
    def action_save_data(self) -> None:
        """Ação para salvar os dados no arquivo JSON."""
        self.save_data()
    
    def action_reload_data(self) -> None:
        """Ação para recarregar os dados do arquivo JSON."""
        self.load_data()
        self.populate_tree()
        self.notify("Dados recarregados do arquivo", severity="information")
    
    def action_add_prompt(self) -> None:
        """Ação para adicionar um novo prompt."""
        if self.current_section:
            path_parts = self.current_section.split(".")
            self.push_screen(EditPromptScreen(path_parts, {}, is_new=True), self.handle_edit_result)
    
    def action_edit_prompt(self) -> None:
        """Ação para editar o prompt selecionado."""
        if self.selected_node and hasattr(self.selected_node, "data") and self.selected_node.data:
            path = self.selected_node.data["path"]
            data = self.selected_node.data["data"]
            self.push_screen(EditPromptScreen(path, data), self.handle_edit_result)
    
    def action_delete_prompt(self) -> None:
        """Ação para excluir o prompt selecionado."""
        if self.selected_node and hasattr(self.selected_node, "data") and self.selected_node.data:
            path = self.selected_node.data["path"]
            self.push_screen(ConfirmDeleteScreen(path), self.handle_delete_result)
    
    def handle_edit_result(self, result) -> None:
        """Manipula o resultado da tela de edição.
        
        Args:
            result: Resultado da operação de edição.
        """
        if result:
            path = result["path"]
            data = result["data"]
            is_new = result["is_new"]
            key_name = result["key_name"]
            self.update_data(path, data, is_new, key_name)
    
    def handle_delete_result(self, confirmed: bool) -> None:
        """Manipula o resultado da tela de confirmação de exclusão.
        
        Args:
            confirmed: Se a exclusão foi confirmada.
        """
        if confirmed and self.selected_node and hasattr(self.selected_node, "data"):
            path = self.selected_node.data["path"]
            self.delete_node(path)


def main():
    """Função principal para executar o aplicativo."""
    try:
        logger.info("INÍCIO - main | Iniciando aplicativo de edição de prompts")
        app = PromptsEditorApp()
        app.run()
        logger.info("FIM - main | Aplicativo finalizado")
    except Exception as e:
        logger.error(f"FALHA - main | Erro ao executar aplicativo: {str(e)}", exc_info=True)
        print(f"Erro ao executar aplicativo: {str(e)}")


if __name__ == "__main__":
    main() 