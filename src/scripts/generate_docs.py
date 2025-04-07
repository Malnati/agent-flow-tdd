#!/usr/bin/env python3
"""
Script para geração automática de documentação via IA.
"""
import sys
from pathlib import Path

def create_section(docs_dir: Path, section: str, content: str) -> None:
    """Cria uma seção da documentação."""
    section_dir = docs_dir / section
    section_dir.mkdir(exist_ok=True)
    
    index_file = section_dir / "index.md"
    index_file.write_text(content)

def generate_docs() -> None:
    """Gera a documentação do projeto."""
    print("🤖 Gerando documentação via IA...")
    
    # Cria diretório docs se não existir
    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)
    
    # Gera index.md
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
    
    index_file = docs_dir / "index.md"
    index_file.write_text(index_content)
    
    # Gera seções
    sections = {
        "overview": """# Visão Geral

## Objetivo

O Agent Flow TDD tem como objetivo facilitar o desenvolvimento de agentes de IA
usando práticas de TDD. O framework fornece uma estrutura que permite:

- Desenvolvimento iterativo e testável de agentes
- Gerenciamento de estado e contexto
- Integração com diferentes modelos de IA
- Monitoramento e logging de operações

## Arquitetura

O framework é organizado em camadas:

1. CLI: Interface de linha de comando
2. Kernel: Núcleo do framework
3. Agents: Implementação dos agentes
4. Database: Persistência de dados
5. MCP: Gerenciamento de processos""",
        
        "installation": """# Instalação

## Dependências

O projeto requer:

- Python 3.10+
- Poetry para gerenciamento de dependências
- SQLite 3.x
- Git

## Ambiente

1. Clone o repositório
2. Instale o Poetry
3. Execute `poetry install`
4. Configure as variáveis de ambiente""",
        
        "usage": """# Uso

## CLI

O framework pode ser usado via CLI:

```bash
agent-flow run --mode interactive
agent-flow run --mode batch
```

## MCP

O Master Control Program (MCP) gerencia os agentes:

```bash
agent-flow mcp start
agent-flow mcp status
agent-flow mcp stop
```""",
        
        "development": """# Desenvolvimento

## Código

O código está organizado em:

- `src/core/`: Núcleo do framework
- `src/agents/`: Implementação dos agentes
- `src/db/`: Camada de banco de dados
- `src/cli/`: Interface de linha de comando

## Local

Para desenvolvimento local:

1. Configure o ambiente de desenvolvimento
2. Execute os testes
3. Implemente novas funcionalidades""",
        
        "testing": """# Testes

## Unitários

Os testes unitários usam pytest:

```bash
make test
```

## Cobertura

A cobertura de código é medida com pytest-cov:

```bash
make coverage
```""",
        
        "database": """# Banco de Dados

## Estrutura

O banco usa SQLite com as tabelas:

- `agents`: Registro de agentes
- `tasks`: Tarefas dos agentes
- `logs`: Log de operações

## SQL

As operações são gerenciadas pela classe DatabaseManager.""",
        
        "logs": """# Logs

## Formato

Os logs seguem o formato:

```json
{
    "timestamp": "2024-03-21T10:00:00Z",
    "level": "INFO",
    "message": "Agent started",
    "context": {}
}
```

## Níveis

- DEBUG: Informações detalhadas
- INFO: Operações normais
- WARNING: Alertas
- ERROR: Erros recuperáveis
- CRITICAL: Erros críticos""",
        
        "deployment": """# Deploy

## Docker

O projeto pode ser containerizado:

```bash
docker build -t agent-flow .
docker run agent-flow
```

## Produção

Para ambiente de produção:

1. Configure variáveis de ambiente
2. Use Docker Compose
3. Configure monitoramento""",
        
        "troubleshooting": """# Troubleshooting

## Erros

Problemas comuns e soluções:

- Erro de conexão: Verifique configurações
- Timeout: Ajuste limites de tempo
- Memória: Monitore uso de recursos

## Fallback

O sistema possui mecanismos de fallback:

1. Retry automático
2. Circuit breaker
3. Modo degradado"""
    }
    
    for section, content in sections.items():
        create_section(docs_dir, section, content)
    
    print("✅ Documentação gerada!")

if __name__ == "__main__":
    try:
        generate_docs()
    except Exception as e:
        print(f"❌ Erro ao gerar documentação: {e}", file=sys.stderr)
        sys.exit(1) 