# Dependências

O Agent Flow TDD possui diversas dependências que são necessárias para seu funcionamento adequado.

## Requisitos do Sistema

- **Python**: Versão 3.13 ou superior
- **Sistema Operacional**: Linux, macOS ou Windows
- **Armazenamento**: Mínimo de 4GB para modelos locais
- **Memória**: Mínimo de 8GB RAM (16GB recomendado)

## Dependências Python

As principais dependências do projeto são:

### Core

- **Pydantic**: Validação de dados e serialização
- **PyYAML**: Processamento de arquivos YAML
- **SQLite3**: Banco de dados para logging (incluído no Python)
- **Rich**: Formatação de texto no terminal
- **Typer**: Criação de interfaces de linha de comando

### Modelos de IA

- **llama-cpp-python**: Interface Python para llama.cpp (modelos locais)
- **openai**: Cliente oficial da OpenAI
- **anthropic**: Cliente oficial da Anthropic
- **google-generativeai**: Cliente oficial do Google AI (Gemini)

### Desenvolvimento

- **pytest**: Framework de testes
- **autoflake**: Remoção de imports não utilizados
- **rope**: Biblioteca para refatoração
- **mkdocs**: Geração de documentação
- **mkdocs-material**: Tema para MkDocs

## Instalação das Dependências

Todas as dependências são gerenciadas pelo `setup.py` e podem ser instaladas automaticamente com:

```bash
# Instalação básica
make install

# Instalação com dependências de desenvolvimento
pip install -e ".[dev]"

# Instalação com dependências de documentação
pip install -e ".[docs]"
```

### Extras Disponíveis

O projeto define os seguintes grupos de dependências extras:

- **dev**: Ferramentas de desenvolvimento (pytest, linters, etc.)
- **docs**: Ferramentas para documentação (mkdocs, etc.)
- **models**: Bibliotecas para modelos adicionais

## Dependências de Sistema (por SO)

### Linux (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install -y build-essential python3-dev python3-venv
```

### macOS

```bash
brew install python
```

### Windows

- Instale o Python 3.13+ do [python.org](https://python.org)
- Instale o [Build Tools for Visual Studio](https://visualstudio.microsoft.com/visual-cpp-build-tools/) para compilar algumas dependências

## Validação de Dependências

O Agent Flow TDD inclui uma ferramenta de diagnóstico para verificar se todas as dependências estão corretamente instaladas:

```bash
make status
```

Este comando verifica:
- Versão do Python
- Dependências instaladas
- Modelos disponíveis
- Variáveis de ambiente configuradas 