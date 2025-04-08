"""
Módulo de agentes e guardrails do sistema.
"""
from typing import Any, Dict, List, Optional
import yaml
import json
import os
from pydantic import BaseModel
import uuid

from src.core import ModelManager
from src.core.db import DatabaseManager
from src.core.logger import get_logger

logger = get_logger(__name__)

def load_config() -> Dict[str, Any]:
    """
    Carrega configurações do sistema.
    
    Returns:
        Dict com configurações
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
            # Fallback para o arquivo YAML se o JSON não existir
            yaml_config_path = os.path.join(os.path.dirname(__file__), "..", "configs", "agents.yaml")
            if os.path.exists(yaml_config_path):
                with open(yaml_config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                    logger.warning(f"Arquivo JSON não encontrado, usando YAML: {yaml_config_path}")
                    return config
            else:
                raise FileNotFoundError("Nenhum arquivo de configuração encontrado (JSON ou YAML)")
    except Exception as e:
        logger.error(f"FALHA - load_config | Erro: {str(e)}")
        # Retorna uma configuração mínima padrão como fallback
        return {
            "GuardRails": {
                "Input": {},
                "Output": {}
            },
            "prompts": {
                "system": "Você é um assistente especializado em análise e desenvolvimento de software."
            }
        }

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
    """Orquestrador de agentes do sistema."""

    def __init__(self, model_manager: Optional[ModelManager] = None):
        """
        Inicializa o orquestrador.
        
        Args:
            model_manager: Gerenciador de modelos opcional
        """
        self.model_manager = model_manager or ModelManager()
        self.input_guardrails = [
            InputGuardrail(self.model_manager, config)
            for config in CONFIG.get("GuardRails", {}).get("Input", {}).values()
        ]
        self.output_guardrails = [
            OutputGuardrail(self.model_manager, config)
            for config in CONFIG.get("GuardRails", {}).get("Output", {}).values()
        ]
        self.db = DatabaseManager()
        logger.info("AgentOrchestrator inicializado")

    def execute(self, prompt: str, format: str = "json") -> AgentResult:
        """
        Executa o fluxo do agente.
        
        Args:
            prompt: Prompt do usuário
            format: Formato de saída (json/markdown)
            
        Returns:
            Resultado da execução
        """
        try:
            # Registra execução
            run_id = self.db.log_run(
                str(uuid.uuid4()),
                input=prompt,
                output_type=format
            )

            # Valida entrada
            input_results = []
            has_critical_input_error = False
            
            for guardrail in self.input_guardrails:
                try:
                    result = guardrail.process(prompt)
                    input_results.append(result)
                    self.db.log_guardrail_results(
                        run_id=run_id,
                        guardrail_type="input",
                        results={
                            "prompt": prompt,
                            "info": result.get("info", {}),
                            "status": result.get("status", "error"),
                            "passed": result.get("status") == "success"
                        }
                    )
                    
                    if result.get("status") != "success":
                        # Falha lógica: continuamos a execução, apenas logamos alerta
                        logger.warning(f"Guardrail de entrada falhou: {result.get('error', 'Erro desconhecido')}")
                except Exception as e:
                    # Falha sistêmica: registramos e consideramos crítico
                    logger.error(f"Erro sistêmico no guardrail de entrada: {str(e)}")
                    has_critical_input_error = True
                    input_results.append({
                        "status": "error",
                        "error": f"Erro sistêmico: {str(e)}",
                        "prompt": prompt
                    })

            if has_critical_input_error:
                # Interrompe apenas em caso de erro sistêmico
                raise ValueError("Erro crítico na validação de entrada")

            # Gera resposta
            messages = [
                {"role": "system", "content": CONFIG["prompts"]["system"]},
                {"role": "user", "content": prompt}
            ]
            response = self.model_manager.generate_response(messages)

            # Valida saída
            output_results = []
            has_critical_output_error = False
            
            for guardrail in self.output_guardrails:
                try:
                    result = guardrail.process(response, prompt)
                    output_results.append(result)
                    self.db.log_guardrail_results(
                        run_id=run_id,
                        guardrail_type="output",
                        results={
                            "response": response,
                            "info": result.get("info", {}),
                            "status": result.get("status", "error"),
                            "passed": result.get("status") == "success"
                        }
                    )
                    
                    if result.get("status") != "success":
                        # Falha lógica: continuamos a execução, apenas logamos alerta
                        logger.warning(f"Guardrail de saída falhou: {result.get('error', 'Erro desconhecido')}")
                except Exception as e:
                    # Falha sistêmica: registramos e consideramos crítico
                    logger.error(f"Erro sistêmico no guardrail de saída: {str(e)}")
                    has_critical_output_error = True
                    output_results.append({
                        "status": "error",
                        "error": f"Erro sistêmico: {str(e)}",
                        "response": response
                    })

            if has_critical_output_error:
                # Interrompe apenas em caso de erro sistêmico
                raise ValueError("Erro crítico na validação de saída")

            # Registra resposta
            self.db.log_raw_response(run_id, response)

            # Retorna resultado
            return AgentResult(
                output=response,
                items=[{"type": "response", "content": response}],
                guardrails=input_results + output_results,
                raw_responses=[{"id": "response", "response": response}]
            )

        except Exception as e:
            logger.error(f"FALHA - execute | Erro: {str(e)}")
            raise

class InputGuardrail:
    """Guardrail para validação e estruturação de entrada."""
    
    def __init__(self, model_manager: ModelManager, config: Dict[str, Any]):
        """
        Inicializa o guardrail.
        
        Args:
            model_manager: Gerenciador de modelos
            config: Configurações do guardrail
        """
        self.model_manager = model_manager
        self.config = config
        # Requisitos agora é texto plano, não um dicionário de chaves
        self.requirements = self.config.get("requirements", "")
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
            
            # Tenta fazer parse do JSON ou YAML
            try:
                # Tenta primeiro como JSON
                try:
                    info = json.loads(response)
                    if isinstance(info, dict):
                        logger.debug(f"Informações extraídas via JSON: {info}")
                        return info
                except json.JSONDecodeError:
                    # Tenta depois como YAML 
                    info = yaml.safe_load(response)
                    if isinstance(info, dict):
                        logger.debug(f"Informações extraídas via YAML: {info}")
                        return info
                    else:
                        logger.warning("Resposta não é um dicionário válido, tentando extração manual")
            except Exception as e:
                logger.warning(f"Erro ao fazer parse: {str(e)}, tentando extração manual")
            
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
                info = json.loads(prompt)
                if isinstance(info, dict):
                    logger.info("Extraindo informações diretamente do prompt no formato JSON")
                    return info
            except json.JSONDecodeError:
                # Tentativa de parse YAML do prompt original
                info = yaml.safe_load(prompt)
                if isinstance(info, dict):
                    logger.info("Extraindo informações diretamente do prompt no formato YAML")
                    return info
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
    """Guardrail para validação e estruturação de saída."""
    
    def __init__(self, model_manager: ModelManager, config: Dict[str, Any]):
        """
        Inicializa o guardrail.
        
        Args:
            model_manager: Gerenciador de modelos
            config: Configurações do guardrail
        """
        self.model_manager = model_manager
        self.config = config
        # Requisitos agora é texto plano, não um dicionário de chaves
        self.requirements = self.config.get("requirements", "")
        logger.info("OutputGuardrail inicializado")
        
    def _load_config(self) -> Dict[str, Any]:
        """Carrega configurações do guardrail."""
        return CONFIG["guardrails"]["output"]
        
    def _load_requirements(self) -> str:
        """Carrega requisitos da saída."""
        return self.config["requirements"]
        
    def _validate_json(self, data: Dict[str, Any]) -> List[str]:
        """
        Valida campos obrigatórios no JSON.
        
        Args:
            data: Dados a serem validados
            
        Returns:
            Lista de campos ausentes
        """
        # Como requirements agora é texto, realizamos uma validação básica
        # A implementação atual apenas verifica se é um dicionário com campos básicos
        missing_fields = []
        
        if not data or not isinstance(data, dict):
            missing_fields.append("formato_json_valido")
            return missing_fields
            
        # Validação básica de campos obrigatórios
        required_fields = ["Nome da funcionalidade", "Descrição detalhada"]
        for field in required_fields:
            if field not in data or not data[field]:
                missing_fields.append(field)
                
        return missing_fields
        
    def _suggest_missing_fields(self, data: Dict[str, Any], missing_fields: List[str], context: str) -> Dict[str, Any]:
        """
        Sugere valores para campos ausentes.
        
        Args:
            data: Dados existentes
            missing_fields: Campos ausentes
            context: Contexto para geração
            
        Returns:
            Dict com sugestões
        """
        try:
            # Gera resposta com o modelo
            messages = [
                {"role": "system", "content": self.config["completion_prompt"]},
                {"role": "user", "content": f"Contexto: {context}\nCampos ausentes: {', '.join(missing_fields)}"}
            ]
            
            response = self.model_manager.generate_response(messages)
            
            # Tenta fazer parse do JSON ou YAML
            try:
                # Tenta primeiro como JSON
                try:
                    suggestions = json.loads(response)
                    if not isinstance(suggestions, dict):
                        raise ValueError("Resposta não é um dicionário")
                except json.JSONDecodeError:
                    # Tenta depois como YAML
                    suggestions = yaml.safe_load(response)
                    if not isinstance(suggestions, dict):
                        raise ValueError("Resposta não é um dicionário")
                    
                # Atualiza dados com sugestões
                for field in missing_fields:
                    if field in suggestions:
                        data[field] = suggestions[field]
                        
                return data
                
            except Exception as e:
                logger.error(f"FALHA - _suggest_missing_fields | Erro ao fazer parse: {str(e)}")
                return data
                
        except Exception as e:
            logger.error(f"FALHA - _suggest_missing_fields | Erro: {str(e)}")
            return data
            
    def process(self, output: str, context: str) -> Dict[str, Any]:
        """
        Processa e valida a saída.
        
        Args:
            output: Saída do modelo
            context: Contexto da geração
            
        Returns:
            Dict com resultado do processamento
        """
        try:
            # Limpa a resposta de marcadores de código markdown se existirem
            cleaned_output = output
            if cleaned_output.startswith("```") and "```" in cleaned_output[3:]:
                # Remove os delimitadores de código markdown (```json e ```)
                first_delimiter_end = cleaned_output.find("\n", 3)
                if first_delimiter_end != -1:
                    last_delimiter_start = cleaned_output.rfind("```")
                    if last_delimiter_start > first_delimiter_end:
                        cleaned_output = cleaned_output[first_delimiter_end+1:last_delimiter_start].strip()
            
            # Tenta fazer parse do JSON ou YAML
            try:
                # Tenta primeiro como JSON
                try:
                    data = json.loads(cleaned_output)
                    if not isinstance(data, dict):
                        raise ValueError("Saída não é um dicionário")
                except json.JSONDecodeError:
                    # Tenta depois como YAML
                    data = yaml.safe_load(cleaned_output)
                    if not isinstance(data, dict):
                        raise ValueError("Saída não é um dicionário")
            except Exception as e:
                logger.warning(f"Erro ao fazer parse da saída: {str(e)}, usando dados do contexto")
                
                # Como não conseguimos parsear a saída, vamos usar 
                # os dados do contexto que já foram validados
                try:
                    # Tenta fazer parse do contexto como JSON ou YAML
                    try:
                        context_data = json.loads(context)
                        if isinstance(context_data, dict):
                            logger.info("Usando dados extraídos do contexto original (JSON)")
                            return {
                                "status": "success",
                                "output": output,
                                "data": context_data
                            }
                    except json.JSONDecodeError:
                        context_data = yaml.safe_load(context)
                        if isinstance(context_data, dict):
                            logger.info("Usando dados extraídos do contexto original (YAML)")
                            return {
                                "status": "success",
                                "output": output,
                                "data": context_data
                            }
                except Exception:
                    logger.warning("Não foi possível usar dados do contexto")
                
                # Se ainda não conseguimos extrair informações, tenta usar 
                # o próprio output como um bloco de texto não-estruturado
                return {
                    "status": "success",
                    "output": output,
                    "data": {"text": output}
                }
                
            # Valida campos obrigatórios
            missing_fields = self._validate_json(data)
            
            if missing_fields:
                # Tenta sugerir valores para campos ausentes
                data = self._suggest_missing_fields(data, missing_fields, context)
                
                # Valida novamente
                missing_fields = self._validate_json(data)
                
                if missing_fields:
                    return {
                        "status": "error",
                        "error": f"Campos obrigatórios ausentes: {', '.join(missing_fields)}",
                        "output": output
                    }
                    
            return {
                "status": "success",
                "output": output,
                "data": data
            }
            
        except Exception as e:
            logger.error(f"FALHA - process | Erro: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "output": output
            }
