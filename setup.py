#!/usr/bin/env python3
"""
Script de instalação do pacote.
"""
import json
import subprocess
import sys
from setuptools import find_packages, setup
from setuptools.command.develop import develop
from setuptools.command.install import install
import pkg_resources
import os

class PreInstallCommand:
    """Classe base para executar comandos antes da instalação."""
    def check_if_installed(self):
        """Verifica se o pacote já está instalado."""
        try:
            pkg_resources.get_distribution('agent-flow-tdd')
            return True
        except pkg_resources.DistributionNotFound:
            return False

    def run_pre_install(self):
        """Executa a limpeza de instalações anteriores."""
        if not self.check_if_installed():
            print("ℹ️  Nenhuma instalação anterior encontrada. Prosseguindo com instalação...")
            return

        print("🧹 Removendo instalação anterior do pacote...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", "agent-flow-tdd"])
            print("✅ Pacote removido com sucesso!")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Erro ao remover pacote: {e}")

# Função para verificar e baixar modelos
class ModelDownloader:
    MODEL_URLS = {
        "tinyllama": "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
        "phi1": "https://huggingface.co/professorf/phi-1-gguf/resolve/main/phi-1-f16.gguf",
        "deepseek": "https://huggingface.co/TheBloke/deepseek-coder-6.7B-instruct-GGUF/resolve/main/deepseek-coder-6.7b-instruct.Q4_K_M.gguf",
        "phi3": "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/Phi-3-mini-4k-instruct-q4.gguf"
    }
    MODEL_DIR = "models"

    @staticmethod
    def download_model(model_name, url):
        model_path = os.path.join(ModelDownloader.MODEL_DIR, f"{model_name}.gguf")
        if not os.path.exists(model_path) or os.path.getsize(model_path) < 1024:
            print(f"📥 Baixando modelo {model_name}...")
            os.makedirs(ModelDownloader.MODEL_DIR, exist_ok=True)
            subprocess.run(["curl", "-L", "-f", url, "-o", model_path], check=True)
            print(f"✅ Modelo {model_name} baixado com sucesso!")
        else:
            print(f"✅ Modelo {model_name} já está disponível.")

    @staticmethod
    def verify_and_download_models():
        for model_name, url in ModelDownloader.MODEL_URLS.items():
            ModelDownloader.download_model(model_name, url)

class CustomInstallCommand(install, PreInstallCommand):
    """Comando customizado para instalação normal."""
    def run(self):
        self.run_pre_install()
        install.run(self)
        ModelDownloader.verify_and_download_models()

class CustomDevelopCommand(develop, PreInstallCommand):
    """Comando customizado para instalação em modo desenvolvimento."""
    def run(self):
        self.run_pre_install()
        develop.run(self)
        ModelDownloader.verify_and_download_models()

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
    "anthropic>=0.18.0",
    "PyYAML>=6.0.1",
    "llama-cpp-python>=0.2.10",
    "textual>=0.44.0",
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
    "build>=1.0.3",
    "twine>=4.0.2",
]

# Dependências para documentação
docs_requires = [
    "mkdocs>=1.5.0",
    "mkdocs-material>=9.5.0",
    "mkdocstrings>=0.24.0",
    "mkdocstrings-python>=1.7.0",
    "mkdocs-gen-files>=0.5.0",
    "mkdocs-literate-nav>=0.6.0",
]

# Dependências opcionais para modelos mais avançados
ml_requires = [
    "transformers>=4.34.0",
    "torch>=2.0.0",
    "accelerate>=0.20.0",
]

# Lê a versão do arquivo .version.json
with open('.version.json', 'r', encoding='utf-8') as f:
    version_data = json.load(f)
    version = version_data['current']

setup(
    name="agent-flow-tdd",
    version=version,
    packages=find_packages(),
    package_data={
        '': ['.version.json'],  # Inclui arquivo de versão na raiz
        'src': ['configs/*.yaml', 'configs/mkdocs.yml'],  # Inclui arquivos YAML e mkdocs.yml do diretório configs
    },
    data_files=[
        ('', ['.version.json']),  # Copia arquivo de versão para a raiz do pacote instalado
    ],
    install_requires=install_requires,
    extras_require={
        "dev": dev_requires,
        "docs": docs_requires,
        "ml": ml_requires,
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
    long_description=open("README.md", encoding='utf-8').read(),
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