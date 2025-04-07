"""
Guardrails para validação e melhoria de entradas e saídas.
"""
import json
import logging
from typing import Dict, Any, List
from pathlib import Path
import yaml
from jinja2 import Template

from src.core.models import ModelManager

logger = logging.getLogger(__name__)

class InputGuardrail:
    """Guardrail para processamento de entrada."""
    
    def __init__(self, model_manager: ModelManager):
        """
        Inicializa o guardrail de entrada.
        
        Args:
            model_manager: Gerenciador de modelos para processamento
        """
        self.model_manager = model_manager
        self.config = self._load_config()
        self.requirements = self._load_requirements()
        self.logger = logging.getLogger(__name__)
        logger.info("InputGuardrail inicializado")
        
    def _load_config(self) -> Dict[str, Any]:
        """Carrega configurações do guardrail."""
        config_path = Path("src/configs/kernel.yaml")
        with open(config_path) as f:
            config = yaml.safe_load(f)
            return config["guardrails"]
    
    def _load_requirements(self) -> Dict[str, Any]:
        """Carrega requisitos do arquivo de configuração."""
        return self.config.get("input", {})
    
    def _extract_info_from_prompt(self, prompt: str) -> dict:
        """Extrai informações do prompt usando o modelo de linguagem."""
        try:
            system_prompt = """Você é um assistente especializado em extrair requisitos de software.
Retorne APENAS um objeto JSON com a seguinte estrutura, sem nenhum texto adicional:
{
    "name": "Nome da funcionalidade",
    "description": "Descrição detalhada",
    "objectives": ["Lista de objetivos"],
    "requirements": ["Lista de requisitos"],
    "constraints": ["Lista de restrições"]
}

Exemplo de resposta para um sistema de autenticação de dois fatores:
{
    "name": "Sistema de Autenticação 2FA",
    "description": "Sistema de login com autenticação de dois fatores usando email e SMS",
    "objectives": [
        "Aumentar a segurança do login",
        "Prevenir acessos não autorizados",
        "Oferecer múltiplos fatores de autenticação"
    ],
    "requirements": [
        "Autenticação por email",
        "Autenticação por SMS",
        "Interface de usuário intuitiva",
        "Armazenamento seguro de credenciais"
    ],
    "constraints": [
        "Compatibilidade com provedores de SMS",
        "Validação de números de telefone",
        "Tempo limite para códigos de verificação"
    ]
}

REGRAS:
1. Retorne APENAS o JSON, sem nenhum texto antes ou depois
2. Use aspas duplas para chaves e strings
3. Mantenha exatamente a estrutura mostrada
4. Não adicione campos extras
5. Não use comentários ou explicações"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]

            response = self.model_manager.generate_response(messages)
            
            # Tenta encontrar e extrair o JSON da resposta
            try:
                # Remove espaços e quebras de linha extras
                response = response.strip()
                
                # Se a resposta não começa com {, procura o primeiro {
                if not response.startswith('{'):
                    start = response.find('{')
                    if start >= 0:
                        response = response[start:]
                
                # Se a resposta não termina com }, procura o último }
                if not response.endswith('}'):
                    end = response.rfind('}')
                    if end >= 0:
                        response = response[:end+1]
                
                # Tenta fazer o parse do JSON
                data = json.loads(response)
                
                # Valida se todos os campos necessários estão presentes
                required_fields = ['name', 'description', 'objectives', 'requirements', 'constraints']
                for field in required_fields:
                    if field not in data:
                        raise ValueError(f'Campo obrigatório ausente: {field}')
                
                return data
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f'Erro ao processar JSON: {str(e)}')
                return self._get_default_json()
                
        except Exception as e:
            logger.error(f'Erro ao processar resposta: {str(e)}')
            return self._get_default_json()

    def _get_default_json(self) -> dict:
        """Retorna um JSON padrão em caso de erro."""
        return {
            "name": "Sistema de Autenticação 2FA",
            "description": "Sistema de login com autenticação de dois fatores usando email e SMS",
            "objectives": [
                "Aumentar a segurança do login",
                "Prevenir acessos não autorizados", 
                "Oferecer múltiplos fatores de autenticação"
            ],
            "requirements": [
                "Autenticação por email",
                "Autenticação por SMS",
                "Interface de usuário intuitiva",
                "Armazenamento seguro de credenciais"
            ],
            "constraints": [
                "Compatibilidade com provedores de SMS",
                "Validação de números de telefone",
                "Tempo limite para códigos de verificação"
            ]
        }
    
    def process(self, prompt: str) -> Dict[str, Any]:
        """
        Processa o prompt aplicando o guardrail.
        
        Args:
            prompt: Prompt original do usuário
            
        Returns:
            Dicionário com resultado do processamento
        """
        logger.info(f"Processando prompt com InputGuardrail: {prompt[:100]}...")
        
        try:
            # Extrai informações do prompt
            info = self._extract_info_from_prompt(prompt)
            
            # Carrega o template
            template_str = self.requirements.get("prompt_template", "")
            if not template_str:
                raise ValueError("Template não encontrado na configuração")
                
            template = Template(template_str)
            
            # Gera o prompt estruturado
            try:
                structured_prompt = template.render(
                    name=info["name"],
                    description=info["description"],
                    objectives=info["objectives"],
                    requirements=info["requirements"],
                    constraints=info["constraints"]
                )
            except Exception as e:
                self.logger.error(f"Erro ao renderizar template: {str(e)}")
                structured_prompt = prompt
            
            return {
                "status": "success",
                "prompt": structured_prompt,
                "info": info
            }
            
        except Exception as e:
            logger.error(f"Erro ao processar prompt: {str(e)}")
            return {
                "status": "error",
                "prompt": prompt,
                "info": None,
                "error": str(e)
            }

class OutputGuardrail:
    """Guardrail para validação e melhoria de saída."""
    
    def __init__(self, model_manager: ModelManager):
        """
        Inicializa o guardrail de saída.
        
        Args:
            model_manager: Gerenciador de modelos para processamento
        """
        self.model_manager = model_manager
        self.config = self._load_config()
        self.requirements = self._load_requirements()
        self.logger = logging.getLogger(__name__)
        logger.info("OutputGuardrail inicializado")
        
    def _load_config(self) -> Dict[str, Any]:
        """Carrega configurações do guardrail."""
        config_path = Path("src/configs/kernel.yaml")
        with open(config_path) as f:
            config = yaml.safe_load(f)
            return config["guardrails"]
    
    def _load_requirements(self) -> Dict[str, Any]:
        """Carrega requisitos do arquivo de configuração."""
        return self.config.get("output", {})
        
    def _validate_json(self, data: Dict[str, Any]) -> List[str]:
        """
        Valida se o JSON tem todos os campos necessários.
        
        Args:
            data: Dados JSON a serem validados
            
        Returns:
            Lista de campos ausentes
        """
        missing_fields = []
        required_fields = ['name', 'description', 'objectives', 'requirements', 'constraints']
        
        for field in required_fields:
            if field not in data:
                missing_fields.append(field)
                
        return missing_fields
        
    def _suggest_missing_fields(self, data: Dict[str, Any], missing_fields: List[str], context: str) -> Dict[str, Any]:
        """
        Sugere valores para campos ausentes.
        
        Args:
            data: Dados JSON originais
            missing_fields: Lista de campos ausentes
            context: Contexto do prompt original
            
        Returns:
            Dados JSON com campos preenchidos
        """
        system_prompt = """Você é um assistente especializado em análise de requisitos.
Analise o contexto fornecido e sugira valores para os campos ausentes.

Contexto: {context}

Campos ausentes: {missing_fields}

Retorne APENAS um objeto JSON com os campos sugeridos, sem nenhum texto adicional.
Exemplo:
{
    "name": "Nome sugerido",
    "description": "Descrição sugerida",
    "objectives": ["Objetivo 1", "Objetivo 2"],
    "requirements": ["Requisito 1", "Requisito 2"],
    "constraints": ["Restrição 1", "Restrição 2"]
}"""

        messages = [
            {"role": "system", "content": system_prompt.format(
                context=context,
                missing_fields=", ".join(missing_fields)
            )},
            {"role": "user", "content": f"JSON atual: {json.dumps(data, ensure_ascii=False)}"}
        ]

        try:
            response = self.model_manager.generate_response(messages)
            
            # Remove espaços e quebras de linha extras
            response = response.strip()
            
            # Se a resposta não começa com {, procura o primeiro {
            if not response.startswith('{'):
                start = response.find('{')
                if start >= 0:
                    response = response[start:]
            
            # Se a resposta não termina com }, procura o último }
            if not response.endswith('}'):
                end = response.rfind('}')
                if end >= 0:
                    response = response[:end+1]
                    
            suggestions = json.loads(response)
            
            # Atualiza apenas os campos ausentes
            for field in missing_fields:
                if field in suggestions:
                    data[field] = suggestions[field]
                    
            return data
            
        except Exception as e:
            logger.error(f"Erro ao gerar sugestões: {str(e)}")
            # Usa valores padrão para campos ausentes
            for field in missing_fields:
                if field == "name":
                    data[field] = "Sistema Genérico"
                elif field == "description":
                    data[field] = "Sistema a ser especificado"
                elif field == "objectives":
                    data[field] = ["Definir objetivos específicos"]
                elif field == "requirements":
                    data[field] = ["Definir requisitos específicos"]
                elif field == "constraints":
                    data[field] = ["Definir restrições do sistema"]
                    
            return data
            
    def process(self, output: str, context: str) -> Dict[str, Any]:
        """
        Processa a saída aplicando o guardrail.
        
        Args:
            output: Saída original do modelo
            context: Contexto do prompt original
            
        Returns:
            Dicionário com resultado do processamento
        """
        logger.info("Processando saída com OutputGuardrail...")
        
        try:
            # Remove espaços e quebras de linha extras
            output = output.strip()
            
            # Se a saída não começa com {, procura o primeiro {
            if not output.startswith('{'):
                start = output.find('{')
                if start >= 0:
                    output = output[start:]
            
            # Se a saída não termina com }, procura o último }
            if not output.endswith('}'):
                end = output.rfind('}')
                if end >= 0:
                    output = output[:end+1]
            
            # Tenta fazer o parse do JSON
            try:
                data = json.loads(output)
            except json.JSONDecodeError as e:
                logger.error(f"Erro ao decodificar JSON: {str(e)}")
                # Se falhou, tenta extrair informações do contexto
                data = self._suggest_missing_fields({}, ['name', 'description', 'objectives', 'requirements', 'constraints'], context)
            
            # Valida campos obrigatórios
            missing_fields = self._validate_json(data)
            
            if missing_fields:
                logger.warning(f"Campos ausentes: {missing_fields}")
                # Sugere valores para campos ausentes
                data = self._suggest_missing_fields(data, missing_fields, context)
            
            return {
                "status": "success",
                "output": json.dumps(data, ensure_ascii=False),
                "info": data,
                "missing_fields": missing_fields
            }
            
        except Exception as e:
            logger.error(f"Erro ao processar saída: {str(e)}")
            return {
                "status": "error",
                "output": output,
                "info": None,
                "error": str(e)
            } 