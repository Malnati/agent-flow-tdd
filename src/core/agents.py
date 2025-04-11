"""
# src/core/agents.py
Módulo de agentes e guardrails do sistema.
"""
from typing import Any, Dict, List, Optional
import json
import os
from pydantic import BaseModel

from src.core import ModelManager
from src.core.logger import get_logger

logger = get_logger(__name__)

def load_config() -> Dict[str, Any]:
    """
    Carrega configurações do sistema.
    
    Returns:
        Dict com configurações
        
    Raises:
        RuntimeError: Quando o arquivo de configuração está ausente ou é inválido
    """
    try:
        # Tenta carregar o arquivo JSON
        agents_config_path = os.path.join(os.path.dirname(__file__), "..", "configs", "agents.json")
        if os.path.exists(agents_config_path):
            with open(agents_config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                logger.info(f"Configurações carregadas com sucesso de: {agents_config_path}")
                return config
        else:
            raise FileNotFoundError(f"Arquivo de configuração não encontrado: {agents_config_path}")
                
    except Exception as e:
        logger.error(f"FALHA - load_config | Erro: {str(e)}")
        raise RuntimeError(f"Erro ao carregar arquivo de configuração: {str(e)}")

# Configurações globais
CONFIG = load_config()

class PromptRequirement(BaseModel):
    """Requisito para estruturação do prompt."""
    name: str
    description: str
    required: bool = True
    value: Optional[str] = None

class AgentResult(BaseModel):
    """Resultado de uma execução do agente."""
    output: Any
    items: List[Dict[str, Any]] = []
    guardrails: List[Dict[str, Any]] = []
    raw_responses: List[Dict[str, Any]] = []

class AgentOrchestrator:
    """
    Classe responsável por orquestrar o fluxo completo de processamento.
    """
    
    def __init__(self, model_name=None):
        """
        Inicializa o orquestrador.
        
        Args:
            model_name: Nome do modelo a ser usado
        """
        self.config = self.load_config()
        self.model_manager = ModelManager(model_name)
        self.input_guardrails = {}
        self.output_guardrails = {}
        self.initialize()
        
    def load_config(self):
        """
        Carrega as configurações do agente, tentando primeiro o JSON.
        
        Returns:
            Configurações carregadas
        """
        try:
            # Tenta carregar do arquivo JSON primeiro
            config_path_json = os.path.join(os.path.dirname(__file__), "../configs/agents.json")
            if os.path.exists(config_path_json):
                with open(config_path_json, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    logger.info(f"Configurações carregadas com sucesso de: {os.path.abspath(config_path_json)}")
                    return config
                    
            # Se nenhum arquivo for encontrado
            raise FileNotFoundError("Arquivos de configuração configs/agents.json não encontrados")
            
        except Exception as e:
            logger.error(f"Erro ao carregar configurações: {str(e)}")
            raise
        
    def execute(self, prompt: str, format: str = "json") -> AgentResult:
        """
        Executa o fluxo completo de processamento.
        
        Args:
            prompt: Prompt do usuário
            format: Formato de saída desejado
            
        Returns:
            Resultado do processamento
        """
        try:
            logger.info(f"Iniciando execução para prompt: {prompt[:50]}...")
            
            # Dicionário para armazenar os resultados dos guardrails de entrada
            guardrail_results = {}
            raw_responses = []
            
            # Processa cada guardrail de entrada dinamicamente
            for guardrail_id, guardrail in self.input_guardrails.items():
                try:
                    result = guardrail.process(prompt)
                    guardrail_results[guardrail_id] = result
                    raw_responses.append({"guardrail": guardrail_id, "response": result})
                    logger.debug(f"Informações extraídas por {guardrail_id}: {result}")
                except Exception as e:
                    logger.warning(f"Falha no guardrail {guardrail_id}: {str(e)}")
                    raw_responses.append({"guardrail": guardrail_id, "error": str(e)})
            
            # Cria um dicionário para agregar as informações coletadas por todos os guardrails
            info = {}
            
            # Percorre todos os resultados dos guardrails dinamicamente
            for guardrail_result in guardrail_results.values():
                # Extrai o campo 'name' se disponível
                if "name" in guardrail_result and not info.get("name"):
                    info["name"] = guardrail_result["name"]
                    
                # Extrai o campo 'description' se disponível
                if "description" in guardrail_result and not info.get("description"):
                    info["description"] = guardrail_result["description"]
                    
                # Extrai o campo 'fields' se disponível
                if "fields" in guardrail_result and not info.get("fields"):
                    info["fields"] = guardrail_result["fields"]
            
            # Verifica se os campos obrigatórios foram extraídos
            if not info.get("name") or not info.get("description"):
                logger.error("Campos obrigatórios (name, description) não encontrados nos resultados dos guardrails")
                return AgentResult(
                    output="Erro na extração de informações mínimas necessárias (nome e descrição)",
                    items=[],
                    guardrails=[],
                    raw_responses=raw_responses
                )
            
            # Gera prompt TDD
            try:
                # Prepara as informações para o guardrail, usando valores padrão caso não encontrados
                title = info.get("name", "")
                description = info.get("description", "")
                fields = info.get("fields", [])
                
                prompt_context = {
                    "title": title,
                    "description": description,
                    "fields": fields
                }
                
                # Formata o prompt para o guardrail
                prompt_for_guardrail = f"""
                Título: {title}
                Descrição: {description}
                Campos: {fields}
                """
                
                # Processa com o guardrail de saída
                result = self.output_guardrails["gerar_prompt_tdd"].process(prompt_for_guardrail, prompt_context)
                
                # Verifica coerência (opcional)
                coherence_result = None
                if "verificar_coerencia" in self.output_guardrails:
                    try:
                        coherence_result = self.output_guardrails["verificar_coerencia"].process(
                            f"Resultado: {result}\nPrompt original: {prompt}", 
                            {"original": prompt, "result": result}
                        )
                        logger.debug(f"Resultado da verificação de coerência: {coherence_result}")
                    except Exception as e:
                        logger.warning(f"Erro na verificação de coerência: {str(e)}")
                
                return AgentResult(
                    output=result,
                    items=[prompt_context],
                    guardrails=[
                        {"name": "gerar_prompt_tdd", "result": result},
                        {"name": "verificar_coerencia", "result": coherence_result} if coherence_result else {}
                    ],
                    raw_responses=raw_responses
                )
                
            except Exception as e:
                logger.error(f"Erro no guardrail de saída: {str(e)}")
                return AgentResult(
                    output=f"Erro na geração do resultado: {str(e)}",
                    items=[],
                    guardrails=[],
                    raw_responses=raw_responses
                )
                
        except Exception as e:
            logger.error(f"FALHA - execute | Erro: {str(e)}")
            raise Exception(f"Erro crítico na validação de saída")

    def initialize(self):
        """
        Inicializa os componentes do agente.
        """
        # Inicializa os guardrails de entrada
        input_guardrails = {}
        for guardrail_id, guardrail_config in self.config["GuardRails"]["Input"].items():
            input_guardrails[guardrail_id] = InputGuardrail(
                guardrail_id=guardrail_id,
                config=guardrail_config,
                model_manager=self.model_manager
            )
            logger.info("InputGuardrail inicializado")
        
        # Inicializa os guardrails de saída
        output_guardrails = {}
        for guardrail_id, guardrail_config in self.config["GuardRails"]["Output"].items():
            output_guardrails[guardrail_id] = OutputGuardrail(
                guardrail_name=guardrail_id,
                config=guardrail_config,
                model_manager=self.model_manager
            )
            logger.info("OutputGuardrail inicializado")
            
        self.input_guardrails = input_guardrails
        self.output_guardrails = output_guardrails
        
        logger.info("AgentOrchestrator inicializado")

class InputGuardrail:
    """Guardrail para validação e estruturação de entrada."""
    
    def __init__(self, guardrail_id: str, config: dict, model_manager):
        """
        Inicializa o guardrail.
        
        Args:
            guardrail_id: ID do guardrail
            config: Configuração do guardrail
            model_manager: Gerenciador de modelos
        """
        self.guardrail_id = guardrail_id
        self.config = config
        self.model_manager = model_manager
        self.requirements = config.get("requirements", "")
        logger.info("InputGuardrail inicializado")
        
    def _load_config(self) -> Dict[str, Any]:
        """Carrega configurações do guardrail."""
        return CONFIG["guardrails"]["input"]
        
    def _load_requirements(self) -> str:
        """Carrega requisitos do prompt."""
        return self.config["requirements"]
        
    def _extract_info_from_prompt(self, prompt: str) -> dict:
        """
        Extrai informações estruturadas do prompt.
        
        Args:
            prompt: Prompt do usuário
            
        Returns:
            Dict com informações extraídas
        """
        try:
            # Log do prompt original para debug
            logger.debug(f"Prompt original: {prompt}")
            
            # Gera resposta com o modelo
            messages = [
                {"role": "system", "content": self.config["system_prompt"]},
                {"role": "user", "content": prompt}
            ]
            
            response = self.model_manager.generate_response(messages)
            logger.debug(f"Resposta do modelo: {response}")
            
            # Tenta fazer parse do JSON, removendo blocos de código se necessário
            cleaned_response = response
            if cleaned_response.startswith("```") and "```" in cleaned_response[3:]:
                # Remove os delimitadores de código markdown (```json e ```)
                first_delimiter_end = cleaned_response.find("\n", 3)
                if first_delimiter_end != -1:
                    last_delimiter_start = cleaned_response.rfind("```")
                    if last_delimiter_start > first_delimiter_end:
                        cleaned_response = cleaned_response[first_delimiter_end+1:last_delimiter_start].strip()
            
            # Tenta primeiro como JSON
            try:
                info = json.loads(cleaned_response)
                if isinstance(info, dict):
                    logger.debug(f"Informações extraídas via JSON: {info}")
                    return info
            except json.JSONDecodeError:
                # Se não for JSON válido, vai para extração manual
                logger.warning(f"Erro ao fazer parse JSON, tentando extração manual")
            
            # Fallback: Extração manual dos campos
            logger.info("Tentando extração manual de campos do texto")
            extracted_info = self._extract_fields_from_text(response, prompt)
            if extracted_info:
                logger.debug(f"Informações extraídas manualmente: {extracted_info}")
                return extracted_info
            else:
                # Se não conseguimos extrair, usamos o prompt original como fallback
                return self._extract_fields_from_prompt(prompt)
                
        except Exception as e:
            logger.error(f"FALHA - _extract_info_from_prompt | Erro: {str(e)}")
            # Tenta extrair do prompt como último recurso
            try:
                extracted = self._extract_fields_from_prompt(prompt)
                if extracted:
                    return extracted
            except:
                pass
            return self._get_default_json()
    
    def _extract_fields_from_text(self, text: str, original_prompt: str) -> dict:
        """
        Extrai campos obrigatórios de um texto não estruturado.
        
        Args:
            text: Texto para extrair informações
            original_prompt: Prompt original como fallback
            
        Returns:
            Dict com informações extraídas
        """
        result = {}
        
        # Primeiro, tentamos extrair diretamente do texto de resposta
        
        # Extrai nome do sistema
        if "name:" in original_prompt.lower():
            # Extrair do prompt original
            lines = original_prompt.split("\n")
            for line in lines:
                if line.lower().startswith("name:"):
                    result["name"] = line.split(":", 1)[1].strip()
                    break
        else:
            # Tentar extrair da resposta
            name_patterns = [
                r"(?i)nome\s*:?\s*(.*?)(?:\n|$)",
                r"(?i)name\s*:?\s*(.*?)(?:\n|$)",
                r"(?i)sistema\s+de\s+(.*?)(?:\n|$|\.)",
                r"(?i)o\s+sistema\s+(.*?)(?:\n|$|\.)",
                r"(?i)the\s+(.*?)\s+system",
            ]
            
            for pattern in name_patterns:
                import re
                match = re.search(pattern, text)
                if match:
                    result["name"] = match.group(1).strip()
                    break
        
        # Extrai descrição
        if "description:" in original_prompt.lower():
            # Extrair do prompt original
            lines = original_prompt.split("\n")
            description_found = False
            description = []
            
            for line in lines:
                if line.lower().startswith("description:"):
                    description_found = True
                    description.append(line.split(":", 1)[1].strip())
                elif description_found and (line.startswith(" ") or line.startswith("\t") or not line.strip()):
                    description.append(line.strip())
                elif description_found:
                    break
                    
            result["description"] = " ".join(description).strip()
        else:
            # Busca no texto gerado
            import re
            description_patterns = [
                r"(?i)descrição\s*:?\s*(.*?)(?:\n\n|$)",
                r"(?i)description\s*:?\s*(.*?)(?:\n\n|$)",
                r"(?i)sistema\s+[^.]*\s+que\s+(.*?)(?:\.|$)",
            ]
            
            for pattern in description_patterns:
                match = re.search(pattern, text)
                if match:
                    result["description"] = match.group(1).strip()
                    break
        
        # Extrai objetivos, requisitos e restrições do prompt original se disponíveis
        lists_to_extract = {
            "objectives": ["objectives", "objetivos", "objetivo"],
            "requirements": ["requirements", "requisitos", "requisito"],
            "constraints": ["constraints", "restrições", "restrição"]
        }
        
        for field, keywords in lists_to_extract.items():
            # Primeiro tentamos extrair do prompt original
            items = self._extract_list_from_prompt(original_prompt, keywords)
            if items:
                result[field] = items
                continue
                
            # Se não encontrou no prompt, tenta extrair do texto
            items = self._extract_list_from_text(text, keywords)
            if items:
                result[field] = items
        
        # Verifica se conseguimos extrair todos os campos obrigatórios
        for field in ["name", "description", "objectives", "requirements", "constraints"]:
            if field not in result or not result[field]:
                logger.warning(f"Campo {field} não encontrado na extração manual")
        
        return result
        
    def _extract_list_from_prompt(self, prompt: str, keywords: list) -> list:
        """
        Extrai uma lista de itens do prompt com base em palavras-chave.
        
        Args:
            prompt: Prompt para extrair
            keywords: Lista de palavras-chave para procurar
            
        Returns:
            Lista de itens extraídos
        """
        lines = prompt.split("\n")
        items = []
        in_section = False
        
        for line in lines:
            line = line.strip()
            
            # Verifica se encontrou a seção pelos marcadores de lista
            if not in_section:
                for keyword in keywords:
                    if line.lower().startswith(f"{keyword}:"):
                        in_section = True
                        break
            # Coleta os itens
            elif line.startswith("-"):
                items.append(line[1:].strip())
            # Saiu da seção se encontrou uma nova linha ou outra seção
            elif not line or ":" in line:
                in_section = False
        
        return items
        
    def _extract_list_from_text(self, text: str, keywords: list) -> list:
        """
        Extrai uma lista de itens do texto com base em palavras-chave.
        
        Args:
            text: Texto para extrair
            keywords: Lista de palavras-chave para procurar
            
        Returns:
            Lista de itens extraídos
        """
        items = []
        import re
        
        for keyword in keywords:
            # Busca por seções como "Objetivos:", "Requisitos:", etc.
            section_pattern = rf"(?i){keyword}[:\s]+\n?((?:(?:\d+\.|\-)[^.]*\n?)+)"
            
            # Também busca por menções em frases como "Os objetivos incluem X, Y e Z"
            mention_pattern = rf"(?i){keyword}[^.]*(?:incluem|são|include|are)[^.]*?([^.]*)"
            
            # Tenta o padrão de seção primeiro
            section_match = re.search(section_pattern, text)
            if section_match:
                section_text = section_match.group(1)
                # Extrai cada item marcado com números ou hífens
                item_matches = re.findall(r"(?:\d+\.|\-)\s*([^.\n]*)", section_text)
                if item_matches:
                    items.extend([item.strip() for item in item_matches])
                    break
            
            # Se não encontrou itens numerados, tenta extrair de menções em frases
            if not items:
                mention_match = re.search(mention_pattern, text)
                if mention_match:
                    mention_text = mention_match.group(1).strip()
                    # Divide por vírgulas ou "e"/"and"
                    item_list = re.split(r',\s*|\s+e\s+|\s+and\s+', mention_text)
                    items.extend([item.strip() for item in item_list if item.strip()])
        
        return items
    
    def _extract_fields_from_prompt(self, prompt: str) -> dict:
        """
        Extrai campos diretamente do prompt original como último recurso.
        
        Args:
            prompt: Prompt original
            
        Returns:
            Dict com informações extraídas
        """
        try:
            # Tentativa de parse JSON do prompt original
            try:
                # Limpa o prompt de marcadores de código markdown se necessário
                cleaned_prompt = prompt
                if cleaned_prompt.startswith("```") and "```" in cleaned_prompt[3:]:
                    # Remove os delimitadores de código markdown
                    first_delimiter_end = cleaned_prompt.find("\n", 3)
                    if first_delimiter_end != -1:
                        last_delimiter_start = cleaned_prompt.rfind("```")
                        if last_delimiter_start > first_delimiter_end:
                            cleaned_prompt = cleaned_prompt[first_delimiter_end+1:last_delimiter_start].strip()
                
                info = json.loads(cleaned_prompt)
                if isinstance(info, dict):
                    logger.info("Extraindo informações diretamente do prompt no formato JSON")
                    return info
            except json.JSONDecodeError:
                # Se não for JSON válido, continua para extração manual
                pass
        except:
            pass
            
        # Se falhar, criamos um dicionário com base em extração manual
        result = {}
        
        lines = prompt.split("\n")
        current_field = None
        list_items = []
        
        for line in lines:
            line = line.strip()
            
            # Pula linhas vazias
            if not line:
                continue
                
            # Verifica se é um cabeçalho de campo
            if ":" in line and not line.startswith("-"):
                # Se estávamos processando uma lista, salva ela
                if current_field and list_items:
                    result[current_field] = list_items
                    list_items = []
                
                # Extrai o novo campo
                parts = line.split(":", 1)
                field_name = parts[0].strip().lower()
                field_value = parts[1].strip() if len(parts) > 1 else ""
                
                # Salva no resultado
                if field_value:
                    result[field_name] = field_value
                    current_field = None
                else:
                    current_field = field_name
                    
            # Se é um item de lista
            elif line.startswith("-") and current_field:
                list_items.append(line[1:].strip())
        
        # Adiciona o último campo de lista se houver
        if current_field and list_items:
            result[current_field] = list_items
            
        logger.info(f"Extraído do prompt original: {result}")
        return result
        
    def _get_default_json(self) -> dict:
        """Retorna JSON padrão para casos de erro."""
        return {
            "type": "feature",
            "description": "",
            "acceptance_criteria": [],
            "test_scenarios": []
        }
        
    def process(self, prompt: str) -> Dict[str, Any]:
        """
        Processa e valida o prompt de entrada.
        
        Args:
            prompt: Prompt do usuário
            
        Returns:
            Dict com resultado do processamento
        """
        try:
            # Extrai informações do prompt
            info = self._extract_info_from_prompt(prompt)
            
            # Valida campos básicos de acordo com requisitos
            missing_fields = []
            required_fields = ["name", "description"]
            for field in required_fields:
                if field not in info or not info[field]:
                    missing_fields.append(field)
                    
            if missing_fields:
                return {
                    "status": "error",
                    "error": f"Campos obrigatórios ausentes: {', '.join(missing_fields)}",
                    "prompt": prompt
                }
                
            return {
                "status": "success",
                "prompt": prompt,
                "info": info
            }
            
        except Exception as e:
            logger.error(f"FALHA - process | Erro: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "prompt": prompt
            }

class OutputGuardrail:
    """
    Classe que implementa o guardrail para verificação da saída.
    """
    
    def __init__(self, guardrail_name: str, config: dict, model_manager):
        """
        Inicializa o guardrail.
        
        Args:
            guardrail_name: Nome do guardrail
            config: Configuração do guardrail
            model_manager: Gerenciador de modelos
        """
        self.name = guardrail_name
        self.config = config
        self.model_manager = model_manager
        self.format = config.get("format", "text")
        self.requirements = config.get("requirements", "")
        
    def _load_config(self) -> Dict[str, Any]:
        """Carrega configurações do guardrail."""
        return CONFIG["guardrails"]["output"]
        
    def _load_requirements(self) -> str:
        """Carrega requisitos da saída."""
        return self.config["requirements"]
        
    def _validate_json(self, data):
        """
        Valida se o JSON tem os campos necessários baseado nos requisitos.
        
        Args:
            data: Dados JSON a serem validados
            
        Returns:
            Dicionário com resultado da validação
        """
        # Campos obrigatórios específicos para TDD
        required_fields = [
            "Nome da funcionalidade",
            "Descrição detalhada",
            "Objetivos principais",
            "Requisitos técnico",
            "Restrições do sistema"
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in data or not data[field]:
                missing_fields.append(field)
        
        if missing_fields:
            return {
                "valid": False,
                "errors": f"Campos obrigatórios ausentes: {', '.join(missing_fields)}"
            }
            
        return {"valid": True}
        
    def process(self, prompt, context: dict = None) -> str:
        """
        Processa o prompt e aplica o guardrail.
        
        Args:
            prompt: Prompt do usuário
            context: Contexto adicional com dados para o guardrail
            
        Returns:
            Resposta validada
        """
        if not context:
            context = {}
        
        try:
            logger.debug(f"Processando guardrail output {self.name}")
            
            # Gera resposta com o modelo
            messages = [
                {"role": "system", "content": self.config["completion_prompt"]},
                {"role": "user", "content": prompt}
            ]
            
            output = self.model_manager.generate_response(messages)
            logger.debug(f"Saída do modelo: {output}")
            
            # Limpa o output se estiver em formato de bloco de código
            cleaned_output = output
            if cleaned_output.startswith("```") and "```" in cleaned_output[3:]:
                first_delimiter_end = cleaned_output.find("\n", 3)
                if first_delimiter_end != -1:
                    last_delimiter_start = cleaned_output.rfind("```")
                    if last_delimiter_start > first_delimiter_end:
                        cleaned_output = cleaned_output[first_delimiter_end+1:last_delimiter_start].strip()
                        logger.debug(f"Output limpo de marcadores de código: {cleaned_output}")
            
            # Validação baseada no formato
            if self.format == "json":
                try:
                    data = json.loads(cleaned_output)
                    validation_result = self._validate_json(data)
                    if validation_result["valid"]:
                        return json.dumps(data, indent=2, ensure_ascii=False)
                    else:
                        logger.warning(f"Validação JSON falhou: {validation_result['errors']}, usando dados do contexto")
                        if context:
                            return json.dumps(context, indent=2, ensure_ascii=False)
                        return output
                except json.JSONDecodeError as e:
                    logger.warning(f"Erro ao fazer parse da saída JSON: {str(e)}, usando dados do contexto")
                    return output
            else:
                # Para formatos não suportados, apenas retorna a saída
                return output
                
        except Exception as e:
            logger.error(f"FALHA - process | Erro: {str(e)}")
            return "Erro ao processar o guardrail de saída"
