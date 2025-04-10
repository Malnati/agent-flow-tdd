# Agent Flow TDD

Framework para desenvolvimento orientado a testes usando agentes de IA.

## 🚀 Visão Geral

O Agent Flow TDD é um framework que utiliza agentes de IA para auxiliar no desenvolvimento orientado a testes (TDD). Ele fornece uma estrutura para criar, testar e implantar aplicações usando prompts de IA.

## 📋 Principais Funcionalidades

- **Desenvolvimento orientado a testes** para agentes de IA
- **Múltiplos modelos** suportados (locais e remotos)
- **Interface CLI** com modo interativo
- **Protocolo MCP** (Model Context Protocol) para integração padronizada
- **Guardrails** para validação de entradas e saídas
- **Logging estruturado** em SQLite
- **Sistema de tracing** e monitoramento
- **Suporte para modelos locais** sem necessidade de APIs externas

## 📚 Documentação

Navegue pelas seções da documentação para aprender mais sobre o Agent Flow TDD:

- [Visão Geral](overview/README.md) - Objetivos, arquitetura e tecnologias
- [Instalação](installation/README.md) - Como instalar e configurar
  - [Publicação do Pacote](installation/README.md#publicação-do-pacote) - Como publicar novas versões
- [Uso](usage/README.md) - Como usar a CLI e o modo MCP
- [Desenvolvimento](development/README.md) - Como desenvolver usando o framework
- [Testes](testing/README.md) - Como testar seus agentes
- [Banco de Dados](database/README.md) - Estrutura e gerenciamento do banco de dados
- [Logs](logs/README.md) - Sistema de logging e monitoramento
- [Deploy](deployment/README.md) - Como implantar em produção
- [Troubleshooting](troubleshooting/README.md) - Resolução de problemas comuns
  - [Erros de Publicação e Build](troubleshooting/common-errors.md#erros-de-publicação-e-build) - Problemas específicos de build e publicação

## ⚙️ Resumo de Comandos

```bash
# Instalar o framework
make install

# Executar um prompt
make tdd prompt="Criar uma API REST" format=json

# Especificar um modelo
make tdd prompt="Ordenação de lista" model=deepseek_local format=python

# Ver logs
make logs

# Publicar uma nova versão (desenvolvedores)
export PYPI_TOKEN="seu-token"
make publish
```

Para mais detalhes, consulte a [seção de Uso](usage/README.md). 

