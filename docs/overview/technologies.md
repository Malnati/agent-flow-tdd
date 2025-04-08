# Tecnologias

O Agent Flow TDD utiliza uma combinação de tecnologias modernas para fornecer uma experiência robusta de desenvolvimento orientado a testes com agentes de IA.

## Stack Tecnológica

### Linguagens

- **Python 3.13+**: Linguagem principal do framework
- **YAML/JSON**: Formatos de configuração e comunicação

### Bibliotecas Principais

- **llama.cpp**: Biblioteca para execução de modelos locais (TinyLLaMA, Phi-1, DeepSeek)
- **OpenAI API**: Integração com modelos GPT
- **Anthropic API**: Integração com modelos Claude
- **Google AI (Gemini) API**: Integração com modelos Gemini
- **SQLite**: Banco de dados para logging estruturado
- **Rich**: Formatação avançada de texto no terminal
- **PyYAML**: Processamento de arquivos YAML
- **Pydantic**: Validação de dados e serialização

### Protocolos e Padrões

- **MCP (Model Context Protocol)**: Protocolo para comunicação padronizada entre componentes
- **TDD (Test-Driven Development)**: Metodologia de desenvolvimento
- **BDD (Behavior-Driven Development)**: Abordagem para descrição de comportamentos
- **JSON Schema**: Validação de estruturas de dados
- **OpenAPI**: Documentação de APIs
- **Semantic Versioning**: Versionamento de releases

## Modelos de IA Suportados

### Modelos Locais

- **TinyLLaMA (1.1B)**: Modelo leve para execução local
- **Phi-1**: Modelo da Microsoft para tarefas gerais
- **DeepSeek Coder (6.7B)**: Especializado em código
- **Phi-3 Mini**: Modelo da Microsoft de última geração

### Modelos Remotos (via API)

- **OpenAI**: GPT-3.5 Turbo, GPT-4 Turbo
- **Anthropic**: Claude 3 (Opus, Sonnet, Haiku)
- **Google AI**: Gemini Pro
- **OpenRouter**: Acesso a múltiplos modelos com uma única API

## Estrutura de Armazenamento

### Banco de Dados

- **SQLite**: Armazenamento local para logs e histórico
- **Tabelas Principais**:
  - `agent_runs`: Execuções de agentes
  - `run_items`: Itens gerados durante a execução
  - `guardrail_results`: Resultados de validações
  - `raw_responses`: Respostas brutas dos modelos
  - `model_cache`: Cache de respostas

### Sistema de Arquivos

- **Logs**: Armazenamento de logs em formato texto
- **Modelos**: Armazenamento de modelos locais
- **Cache**: Cache de respostas e dados intermediários
- **Configurações**: Arquivos YAML de configuração

## Ferramentas de Desenvolvimento

- **pytest**: Framework de testes
- **autoflake**: Remoção de imports não utilizados
- **black**: Formatação de código
- **isort**: Ordenação de imports
- **flake8**: Linting de código
- **mypy**: Verificação de tipos
- **mkdocs**: Geração de documentação
- **rope**: Refatoração de código

## Integração e Deploy

- **GitHub Actions**: CI/CD
- **Docker**: Containerização
- **PyPI**: Distribuição do pacote
- **GitHub Pages**: Hospedagem de documentação 