# Prompt TDD

Um sistema para desenvolvimento orientado a testes usando prompts de IA.

## 🚀 Funcionalidades

- Geração de features com critérios de aceite e cenários de teste
- Análise de complexidade e estimativas
- Suporte a múltiplos modelos de IA (GPT-3.5, GPT-4)
- Interface CLI com modo interativo e MCP (Multi-Command Protocol)
- Saída em formatos JSON e Markdown
- Configuração unificada e centralizada

## 📋 Pré-requisitos

- Python 3.13+
- Chave de API OpenAI (`OPENAI_API_KEY`)
- Ambiente virtual Python (venv)

## 🛠️ Instalação

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/prompt-tdd.git
cd prompt-tdd
```

2. Configure as variáveis de ambiente necessárias:
```bash
# Não use arquivos .env, configure diretamente no ambiente
export OPENAI_API_KEY="sua-chave-aqui"
```

3. Instale as dependências:
```bash
make install
```

## ⚙️ Configuração

O projeto usa um arquivo de configuração unificado em `src/configs/cli.yaml` com três seções principais:

### 1. CLI (`cli`)
- Configurações de saída (formatos, indentação)
- Configurações do modelo (nome, temperatura)
- Mensagens do sistema
- Formatação JSON

### 2. MCP (`mcp`)
- Configurações de logging do MCP
- Configurações do LLM
- Configurações do handler MCP
- Formatos de metadados

### 3. Aplicação (`app`)
- Configurações do modelo
- Configurações do banco de dados
- Configurações de logging
- Configurações de exemplo
- Configurações de resultado

## 🎮 Comandos Disponíveis

### `make install`
Instala todas as dependências do projeto.

```bash
make install
```

### `make test`
Executa todos os testes do projeto.

```bash
make test
```

### `make cli`
Inicia o CLI para processamento de features.

```bash
make cli

# Exemplos de uso:
prompt-tdd feature "Criar sistema de login com autenticação de dois fatores"
prompt-tdd feature "Criar sistema de cadastro de usuários" --model gpt-4-turbo
prompt-tdd feature "Criar API REST" --format markdown
prompt-tdd status
```

#### Opções do comando `feature`:
- `--model, -m`: Modelo a ser usado (default: gpt-3.5-turbo)
- `--elevation-model, -e`: Modelo para fallback (default: gpt-4-turbo)
- `--force, -f`: Força uso do modelo sem fallback
- `--api-key, -k`: Chave da API (opcional)
- `--timeout, -t`: Tempo limite em segundos (default: 30)
- `--max-retries, -r`: Máximo de tentativas (default: 3)
- `--temperature, -temp`: Temperatura do modelo (default: 0.7)
- `--max-tokens, -mt`: Limite de tokens (opcional)
- `--format, -fmt`: Formato de saída (json/markdown)

### Protocolo MCP (Model Context Protocol)

O projeto agora suporta o [Model Context Protocol](https://github.com/modelcontextprotocol/protocol) oficial, permitindo:
- Integração padronizada com diferentes modelos de IA
- Comunicação bidirecional via protocolo MCP
- Suporte a streaming e eventos assíncronos

#### Como Funciona

1. Inicie o modo MCP:
```bash
prompt-tdd mcp
```

2. Envie mensagens no formato MCP:
```json
{
  "content": "Criar sistema de login",
  "metadata": {
    "type": "feature",
    "options": {
      "model": "gpt-4-turbo",
      "temperature": 0.7,
      "format": "json"
    }
  }
}
```

3. Receba respostas no formato MCP:
```json
{
  "content": {
    "feature": "Sistema de Login",
    "acceptance_criteria": [...],
    "test_scenarios": [...],
    "complexity": 3
  },
  "metadata": {
    "status": "success",
    "type": "feature"
  }
}
```

## 🤖 Integração de Modelos

O projeto usa o Model Context Protocol para integração com diferentes modelos:

### 1. Via SDK MCP

```python
from src.core.agents import AgentOrchestrator
from src.core.models import ModelManager
from src.core.db import DatabaseManager

# Inicializa componentes
model_manager = ModelManager()
db = DatabaseManager()

# Cria orquestrador
orchestrator = AgentOrchestrator(model_manager, db)

# Executa
result = orchestrator.execute(
    prompt="Criar sistema de login",
    session_id="exemplo",
    format="json"
)

# Processa resultado
print(f"Saída: {result.output}")
print(f"Items: {len(result.items)}")
print(f"Guardrails: {len(result.guardrails)}")
print(f"Respostas: {len(result.raw_responses)}")
```

### 2. Via CLI

```bash
# OpenAI GPT-4
prompt-tdd feature "Criar API" --model gpt-4-turbo --api-key $OPENAI_API_KEY

# Anthropic Claude
prompt-tdd feature "Criar API" --model claude-3 --api-key $ANTHROPIC_KEY
```

### 3. Via MCP

Especifique o modelo nas options:

```json
{
  "content": "Criar API REST",
  "metadata": {
    "type": "feature",
    "options": {
      "model": "gpt-4-turbo",
      "api_key": "sua-chave",
      "temperature": 0.7
    }
  }
}
```

### Modelos Suportados

O sistema suporta vários modelos de IA que podem ser especificados no parâmetro `model`:

#### Modelos Locais:
- `tinyllama-1.1b` - Modelo local TinyLLaMA, leve e rápido
- `phi-1` - Modelo local Phi-1 da Microsoft
- `deepseek-coder-6.7b` - Modelo local DeepSeek Coder especializado em código
- `phi3-mini` - Modelo local Phi-3 Mini da Microsoft

#### Modelos Remotos:
- `gpt-3.5-turbo` - OpenAI GPT-3.5 Turbo (requer chave OpenAI)
- `gpt-4` - OpenAI GPT-4 (requer chave OpenAI)
- `gemini-pro` - Google Gemini Pro (requer chave Gemini)
- `claude-3-opus` - Anthropic Claude 3 Opus (requer chave Anthropic)

### Exemplo de uso com modelo específico:

```bash
# Usando modelo local
make tdd prompt="Cadastro de pessoas" format=json model="deepseek-coder-6.7b"

# Usando modelo remoto
make tdd prompt="Cadastro de pessoas" format=markdown model="gpt-4"
```

### Configuração de Modelos Adicionais

Cada modelo pode ser baixado separadamente:

```bash
# Baixar TinyLLaMA
make download-model

# Baixar Phi-1
make download-phi1

# Baixar DeepSeek Coder
make download-deepseek

# Baixar Phi-3 Mini
make download-phi3
```

## 🧪 Testes

O projeto usa pytest para testes. Execute:

```bash
make test
```

### Testes Opcionais

Alguns testes são desabilitados por padrão por serem muito lentos. Para executá-los:

```bash
# Executa testes de instalação
pytest -v -m "install" src/tests/test_e2e.py
```

## 📝 Logs

Os logs são gerados automaticamente com:
- Nível INFO para entrada/saída de funções
- Nível DEBUG para estados intermediários
- Nível ERROR para exceções (com stacktrace)
- Configuração centralizada em `cli.yaml`

## 🔒 Variáveis de Ambiente

Variáveis obrigatórias:
- `OPENAI_API_KEY`: Chave da API OpenAI

Variáveis opcionais:
- `OPENROUTER_KEY`: Chave da API OpenRouter
- `GEMINI_KEY`: Chave da API Gemini
- `ANTHROPIC_KEY`: Chave da API Anthropic
- `LOG_LEVEL`: Nível de log (default: INFO)
- `CACHE_DIR`: Diretório de cache
- `CACHE_TTL`: Tempo de vida do cache
- `FALLBACK_ENABLED`: Habilita fallback de modelos
- `DEFAULT_MODEL`: Modelo padrão
- `ELEVATION_MODEL`: Modelo para fallback
- `MODEL_TIMEOUT`: Timeout para chamadas de modelo
- `MAX_RETRIES`: Máximo de tentativas

**IMPORTANTE**: Não use arquivos .env. Configure as variáveis diretamente no ambiente ou via argumentos.

## 🤝 Contribuindo

1. Fork o projeto
2. Crie sua branch de feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## Uso

O Prompt TDD pode ser usado de duas formas:

### 1. Usando o Makefile (recomendado)

```bash
# Criar uma nova feature
make run prompt-tdd="Criar um sistema de login com autenticação JWT"

# Verificar status do ambiente
make run prompt-tdd="" mode=status

# Iniciar servidor MCP em background (sem saída no terminal)
make run prompt-tdd="" mode=mcp
# O servidor MCP será iniciado em background e você verá apenas o PID do processo
```

### 2. Usando o comando diretamente

Primeiro, ative o ambiente virtual:

```bash
source .venv/bin/activate
```

Então use o comando `prompt-tdd`:

```bash
# Criar uma nova feature
prompt-tdd "Criar um sistema de login com autenticação JWT"

# Verificar status do ambiente
prompt-tdd --mode status ""

# Iniciar servidor MCP (irá bloquear o terminal e mostrar logs)
prompt-tdd --mode mcp ""

# Ou inicie em background sem logs
nohup prompt-tdd --mode mcp "" > /dev/null 2>&1 &
```

## Opções

- `--format`: Formato de saída (json ou markdown). Padrão: json
- `--mode`: Modo de operação (feature, status ou mcp). Padrão: feature

## Testes

```bash
make test
```

## Limpeza

```bash
make clean
```

# Agent Flow TDD

<p align="center">
  <img src="assets/logo.png" alt="Agent Flow TDD Logo" width="400">
</p>

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

## 🚀 Início Rápido

```bash
# Clone o repositório
git clone https://github.com/Malnati/agent-flow-tdd.git
cd agent-flow-tdd

# Instale as dependências
make install

# Execute o comando principal
make tdd prompt="Criar API REST" format=json
```

## 📖 Documentação

A documentação completa está disponível no diretório [docs/](docs/):

- [Visão Geral](docs/overview/README.md) - Objetivos, arquitetura e tecnologias
- [Instalação](docs/installation/README.md) - Como instalar e configurar
- [Uso](docs/usage/README.md) - Como usar a CLI e o modo MCP
- [Banco de Dados](docs/database/README.md) - Estrutura e gerenciamento do banco de dados
- [Logs](docs/logs/README.md) - Sistema de logging e monitoramento
- [Troubleshooting](docs/troubleshooting/README.md) - Resolução de problemas comuns

## 💻 Modelos Suportados

O sistema suporta diversos modelos de IA que podem ser utilizados através do parâmetro `model`:

### Modelos Locais
- `tinyllama-1.1b` - Modelo local TinyLLaMA (1.1B)
- `phi1` - Modelo local Phi-1 da Microsoft (1.3B)
- `phi2` - Modelo local Phi-2 da Microsoft (2.7B)
- `deepseek_local` - Modelo local DeepSeek Coder (6.7B)
- `phi3` - Modelo local Phi-3 Mini da Microsoft

### Modelos Remotos (API)
- `gpt-3.5-turbo` e `gpt-4-turbo` - OpenAI
- `claude-3-opus`, `claude-3-sonnet` - Anthropic
- `gemini-pro` - Google

## 🛠️ Comandos Principais

```bash
# Executar o comando principal
make tdd prompt="Criar um sistema de login" format=json

# Especificar um modelo
make tdd prompt="Criar API REST" model=deepseek_local

# Verificar status do ambiente
make status

# Executar testes
make test

# Visualizar logs
make logs
```

## 🤝 Contribuição

Contribuições são bem-vindas! Consulte [docs/development/README.md](docs/development/README.md) para instruções sobre como contribuir para o projeto.

## 📝 Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo LICENSE para mais detalhes.

## 🐳 Usando com Docker

### Pré-requisitos
- Docker
- Docker Compose

### Configuração
1. Copie o arquivo de exemplo de variáveis de ambiente:
```bash
cp .docker/.env.example .docker/.env
```

2. Configure suas chaves de API no arquivo `.docker/.env`:
```env
# Chaves de API
OPENAI_API_KEY=sua-chave-openai
ANTHROPIC_KEY=sua-chave-anthropic
GEMINI_KEY=sua-chave-gemini

# Configurações do modelo
DEFAULT_MODEL=gpt-3.5-turbo
ELEVATION_MODEL=gpt-4-turbo

# Configurações do banco
DB_PATH=/app/data/database.db
DB_HISTORY_LIMIT=100

# Configurações de logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Executando
Para desenvolvimento:
```bash
docker-compose -f .docker/docker-compose.yml run dev
```

Para produção:
```bash
docker-compose -f .docker/docker-compose.yml run app
```

### Exemplo de uso com Docker
```python
from src.core.agents import AgentOrchestrator
from src.core.models import ModelManager
from src.core.db import DatabaseManager

# Inicializa componentes
model_manager = ModelManager()
db = DatabaseManager()

# Cria orquestrador
orchestrator = AgentOrchestrator(model_manager, db)

# Executa
result = orchestrator.execute(
    prompt="Criar sistema de login",
    session_id="docker-exemplo",
    format="json"
)

# Processa resultado
print(f"Saída: {result.output}")
print(f"Items: {len(result.items)}")
print(f"Guardrails: {len(result.guardrails)}")
print(f"Respostas: {len(result.raw_responses)}")
```

### Comandos Úteis
- Construir as imagens:
```bash
docker-compose -f .docker/docker-compose.yml build
```

- Visualizar logs:
```bash
docker-compose -f .docker/docker-compose.yml logs -f
```

- Limpar volumes:
```bash
docker-compose -f .docker/docker-compose.yml down -v
```