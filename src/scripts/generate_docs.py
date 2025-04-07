#!/usr/bin/env python3
"""
Script para geração automática de documentação usando IA.
"""
import json
import logging
import os
from pathlib import Path

from src.core.kernel import AgentOrchestrator
from src.core.db import DatabaseManager

logger = logging.getLogger(__name__)

class DocsGenerator:
    """Gerador de documentação usando IA."""

    def __init__(self):
        """Inicializa o gerador de documentação."""
        self.orchestrator = AgentOrchestrator()
        self.db = DatabaseManager()
        self.docs_dir = Path("docs")
        self.sections = [
            ("overview", ["index", "objective", "architecture", "technologies"]),
            ("installation", ["index", "dependencies", "virtualenv", "environment"]),
            ("usage", ["index", "cli", "mcp", "examples"]),
            ("development", ["index", "code-organization", "local-execution", "docker", "makefile"]),
            ("testing", ["index", "unit-tests", "coverage", "e2e-tests"]),
            ("database", ["index", "structure", "sql-scripts", "manager", "makefile"]),
            ("logs", ["index", "format", "cli", "levels", "storage"]),
            ("deployment", ["index", "docker", "production", "github-pages"]),
            ("troubleshooting", ["index", "common-errors", "fallback", "execution-logs"])
        ]

    def generate_section(self, section: str, subsection: str) -> None:
        """Gera uma seção da documentação.
        
        Args:
            section: Nome da seção principal
            subsection: Nome da subseção
        """
        logger.info(f"Gerando documentação: {section}/{subsection}")
        
        # Cria diretório se não existir
        section_dir = self.docs_dir / section
        section_dir.mkdir(parents=True, exist_ok=True)
        
        # Gera prompt para a IA
        prompt = {
            "content": f"Gerar documentação para {section}/{subsection}",
            "metadata": {
                "type": "docs",
                "section": section,
                "subsection": subsection,
                "options": {
                    "model": "tinyllama-1.1b",
                    "format": "markdown"
                }
            }
        }
        
        # Envia para o orquestrador
        try:
            result = self.orchestrator.handle_input(json.dumps(prompt))
            if isinstance(result, str):
                result = json.loads(result)
            
            # Salva arquivo markdown
            output_file = section_dir / f"{subsection}.md"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(result["content"])
            
            logger.info(f"✅ Documentação gerada: {output_file}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar documentação {section}/{subsection}: {e}")
            raise

    def generate_all(self) -> None:
        """Gera toda a documentação."""
        logger.info("🚀 Iniciando geração de documentação...")
        
        # Gera página inicial
        self.generate_section("", "index")
        
        # Gera todas as seções
        for section, subsections in self.sections:
            for subsection in subsections:
                self.generate_section(section, subsection)
        
        logger.info("✅ Geração de documentação concluída!")

def main():
    """Função principal."""
    # Configura logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Gera documentação
    generator = DocsGenerator()
    generator.generate_all()

if __name__ == "__main__":
    main() 