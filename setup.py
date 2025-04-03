#!/usr/bin/env python3
"""
Script de instalação do pacote.
"""
import subprocess
import sys
from setuptools import find_packages, setup
from setuptools.command.develop import develop
from setuptools.command.install import install

class PreInstallCommand:
    """Classe base para executar comandos antes da instalação."""
    def run_pre_install(self):
        """Executa a limpeza de instalações anteriores."""
        print("🧹 Removendo instalações anteriores do pacote...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", "agent-flow-tdd"])
            print("✅ Pacote removido com sucesso!")
        except subprocess.CalledProcessError:
            print("ℹ️  Nenhuma instalação anterior encontrada.")

class CustomInstallCommand(install, PreInstallCommand):
    """Comando customizado para instalação normal."""
    def run(self):
        self.run_pre_install()
        install.run(self)

class CustomDevelopCommand(develop, PreInstallCommand):
    """Comando customizado para instalação em modo desenvolvimento."""
    def run(self):
        self.run_pre_install()
        develop.run(self)

# Dependências principais
install_requires = [
    "typer>=0.9.0",
    "rich>=13.7.0",
    "openai>=1.12.0",
    "openrouter>=1.0.0",
    "google-generativeai>=0.8.0",
    "python-dotenv>=1.0.0",
    "pydantic>=2.6.0",
    "requests>=2.31.0",
    "tenacity>=8.2.0",
    "cachetools>=5.3.0",
]

# Dependências de desenvolvimento
dev_requires = [
    "pytest>=8.0.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.12.0",
    "black>=23.0.0",
    "isort>=5.12.0",
    "flake8>=6.1.0",
    "mypy>=1.5.0",
    "autoflake>=2.2.0",
]

setup(
    name="agent-flow-tdd",
    version="0.1.0",
    packages=find_packages(),
    install_requires=install_requires,
    extras_require={
        "dev": dev_requires
    },
    entry_points={
        "console_scripts": [
            "agent-flow-tdd=src.cli:app"
        ]
    },
    python_requires=">=3.8",
    author="Seu Nome",
    author_email="seu.email@exemplo.com",
    description="Framework para desenvolvimento orientado a testes com agentes de IA",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/seu-usuario/agent-flow-tdd",
    cmdclass={
        'install': CustomInstallCommand,
        'develop': CustomDevelopCommand,
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
) 