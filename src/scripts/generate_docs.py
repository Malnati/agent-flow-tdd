#!/usr/bin/env python3
"""
Script para geração automática de documentação via IA.
"""
import sys
from pathlib import Path

from src.core.agents import AgentOrchestrator
from src.core.models import ModelManager
from src.core.db import DatabaseManager
from src.core.logger import get_logger

logger = get_logger(__name__)

class DocsGenerator:
    """Gerador de documentação via IA."""
    
    def __init__(self, model_manager: ModelManager = None, db_manager: DatabaseManager = None, docs_dir: Path = None):
        """
        Inicializa o gerador de documentação.
        
        Args:
            model_manager: Gerenciador de modelos
            db_manager: Gerenciador de banco de dados
            docs_dir: Diretório base para documentação
        """
        self.model_manager = model_manager or ModelManager()
        self.db = db_manager or DatabaseManager()
        self.orchestrator = AgentOrchestrator(self.model_manager)
        self.orchestrator.db = self.db
        self.docs_dir = docs_dir or Path("docs")
        logger.info("DocsGenerator inicializado")
        
    def generate_section(self, section: str, subsection: str = None) -> None:
        """
        Gera uma seção da documentação.
        
        Args:
            section: Nome da seção
            subsection: Nome da subseção (opcional)
        """
        try:
            # Monta prompt para o modelo
            prompt = f"Gerar documentação para a seção '{section}'"
            if subsection:
                prompt += f", subseção '{subsection}'"
                
            # Executa o orquestrador
            result = self.orchestrator.execute(
                prompt=prompt,
                session_id="docs_generation",
                format="markdown"
            )
            
            # Cria diretório da seção
            section_dir = self.docs_dir / section
            section_dir.mkdir(parents=True, exist_ok=True)
            
            # Define arquivo de saída
            if subsection:
                output_file = section_dir / f"{subsection}.md"
            else:
                output_file = section_dir / "README.md"
                
            # Salva conteúdo
            output_file.write_text(result.output)
            logger.info(f"Documentação gerada: {output_file}")
            
        except Exception as e:
            error_msg = f"Erro ao gerar seção {section}: {str(e)}"
            logger.error(error_msg)
            print(error_msg, file=sys.stderr)
            raise
            
    def generate_docs(self) -> None:
        """Gera a documentação completa do projeto."""
        try:
            print("🤖 Gerando documentação via IA...")
            
            # Cria diretório docs se não existir
            self.docs_dir.mkdir(parents=True, exist_ok=True)
            
            # Gera seções principais
            sections = [
                "overview",
                "installation",
                "usage",
                "development",
                "testing",
                "database",
                "logs",
                "deployment",
                "troubleshooting"
            ]
            
            for section in sections:
                self.generate_section(section)
                
            # Gera README.md
            index_content = """# Agent Flow TDD

Framework para desenvolvimento de agentes de IA usando Test-Driven Development.

## Sobre o Projeto

O Agent Flow TDD é um framework que facilita o desenvolvimento de agentes de IA
seguindo práticas de TDD (Test-Driven Development). Ele fornece uma estrutura
organizada e ferramentas para criar, testar e implantar agentes de IA de forma
sistemática e confiável.

## Navegação

- [Visão Geral](overview/): Arquitetura e conceitos do framework
- [Instalação](installation/): Como instalar e configurar
- [Uso](usage/): Como usar o framework
- [Desenvolvimento](development/): Guia para desenvolvedores
- [Testes](testing/): Estratégias de teste
- [Banco de Dados](database/): Estrutura e operações
- [Logs](logs/): Sistema de logging
- [Deploy](deployment/): Implantação em produção
- [Troubleshooting](troubleshooting/): Resolução de problemas
"""
            
            index_file = self.docs_dir / "README.md"
            index_file.write_text(index_content)
            
            print("✅ Documentação gerada com sucesso!")
            
        except Exception as e:
            error_msg = f"❌ Erro ao gerar documentação: {str(e)}"
            logger.error(error_msg)
            print(error_msg, file=sys.stderr)
            sys.exit(1)
            
        finally:
            if hasattr(self, 'db'):
                self.db.close()

def main():
    """Função principal."""
    try:
        generator = DocsGenerator()
        generator.generate_docs()
        
    except Exception as e:
        error_msg = f"❌ Erro: {str(e)}"
        print(error_msg, file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 