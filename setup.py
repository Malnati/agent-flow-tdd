#!/usr/bin/env python3
"""
Script de instalação do pacote.
"""
from setuptools import find_packages, setup

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