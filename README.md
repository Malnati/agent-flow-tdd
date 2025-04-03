# Prompt TDD

Um sistema para desenvolvimento orientado a testes usando prompts de IA.

## 🚀 Funcionalidades

- Geração de features com critérios de aceite e cenários de teste
- Análise de complexidade e estimativas
- Suporte a múltiplos modelos de IA (GPT-3.5, GPT-4)
- Interface CLI com modo interativo e MCP (Multi-Command Protocol)
- Saída em formatos JSON e Markdown

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

2. Crie um arquivo `.env` com sua chave da API do OpenAI:
```bash
cp .env.example .env
# Edite o arquivo .env e adicione sua chave da API
```

3. Instale as dependências:
```bash
make install
```

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
from mcp_sdk import MCPHandler
from src.app import AgentOrchestrator

handler = MCPHandler()
handler.initialize(api_key="sua-chave")
handler.run()
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

Atualmente:
- OpenAI GPT-3.5 Turbo
- OpenAI GPT-4 Turbo
- Anthropic Claude (via MCP)
- Outros modelos compatíveis com MCP

## 🧪 Testes

O projeto usa pytest para testes. Execute:

```bash
make test
```

## 📝 Logs

Os logs são gerados automaticamente com:
- Nível INFO para entrada/saída de funções
- Nível DEBUG para estados intermediários
- Nível ERROR para exceções (com stacktrace)

## 🔒 Variáveis de Ambiente

- `OPENAI_API_KEY`: Chave da API OpenAI (obrigatória)
- `ELEVATION_MODEL`: Modelo para fallback (opcional)

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

Framework para desenvolvimento orientado a testes com agentes de IA.

## Recursos

- Desenvolvimento orientado a testes para agentes de IA
- Integração com OpenAI Agent SDK
- Logging estruturado em SQLite
- Suporte a múltiplos provedores de LLM
- Sistema de tracing e monitoramento
- Interface MCP (Model Context Protocol)

## Instalação

```bash
# Instalação básica
pip install agent-flow-tdd

# Instalação com dependências de desenvolvimento
pip install agent-flow-tdd[dev]
```

## Uso Básico

```python
from src.app import AgentOrchestrator

# Inicializa o orquestrador
orchestrator = AgentOrchestrator(api_key="sua-chave-api")

# Processa uma entrada
result = orchestrator.handle_input("Criar sistema de login")
print(result)
```

## Logging Estruturado

O framework inclui um sistema de logging estruturado que armazena todas as interações em SQLite:

### Dados Armazenados

- **Execuções de Agentes**
  - Session ID
  - Input/Output
  - Último agente executado
  - Tipo de saída
  - Timestamp

- **Itens Gerados**
  - MessageOutput
  - HandoffCall/HandoffOutput
  - ToolCall/ToolCallOutput
  - ReasoningItem

- **Guardrails**
  - Resultados de input/output
  - Mensagens de validação

- **Respostas Brutas**
  - Respostas do LLM
  - Metadados de execução

### Consulta de Logs

```python
from src.core.db import DatabaseManager

# Inicializa o gerenciador
db = DatabaseManager()

# Busca histórico de execuções
history = db.get_run_history(limit=10)

# Exemplo de processamento
for run in history:
    print(f"Execução {run['id']}:")
    print(f"- Input: {run['input']}")
    print(f"- Agente: {run['last_agent']}")
    print(f"- Items gerados: {len(run['items'])}")
    print(f"- Guardrails: {len(run['guardrails'])}")
    print(f"- Respostas: {len(run['raw_responses'])}")
```

### Schema SQL

```sql
-- Tabela principal de execuções
CREATE TABLE agent_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    session_id TEXT NOT NULL,
    input TEXT NOT NULL,
    last_agent TEXT,
    output_type TEXT,
    final_output TEXT
);

-- Tabela de itens gerados
CREATE TABLE run_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    item_type TEXT NOT NULL,
    raw_item TEXT NOT NULL,
    source_agent TEXT,
    target_agent TEXT,
    FOREIGN KEY(run_id) REFERENCES agent_runs(id)
);

-- Tabela de resultados de guardrails
CREATE TABLE guardrail_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    guardrail_type TEXT CHECK(guardrail_type IN ('input', 'output')),
    results TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES agent_runs(id)
);

-- Tabela de respostas brutas do LLM
CREATE TABLE raw_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    response TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES agent_runs(id)
);
```

## Desenvolvimento

### Configuração do Ambiente

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/agent-flow-tdd.git
cd agent-flow-tdd

# Crie um ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Instale em modo desenvolvimento
pip install -e ".[dev]"
```

### Executando Testes

```bash
# Executa todos os testes
make test

# Executa testes com cobertura
pytest --cov=src tests/

# Executa testes específicos
pytest tests/test_db.py -v
```

### Linting e Formatação

```bash
# Formata o código
make format

# Executa linters
make lint

# Limpa imports não utilizados
make autoflake
```

## Contribuindo

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -am 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Crie um Pull Request

## Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## Visualização de Logs

O framework inclui um visualizador de logs que permite consultar o histórico de execuções dos agentes. Para usar:

```bash
# Lista as últimas 10 execuções
make logs

# Lista as últimas N execuções
make logs ARGS="--limit 20"

# Filtra por session ID
make logs ARGS="--session abc123"

# Filtra por agente
make logs ARGS="--agent CodeReviewer"

# Mostra detalhes de uma execução específica
make logs ARGS="--id 42"
```

O visualizador mostra:
- Lista resumida de execuções com timestamp, session, agente e contadores
- Detalhes completos de uma execução específica incluindo:
  - Input/output
  - Itens gerados entre agentes
  - Resultados de guardrails
  - Respostas brutas do LLM

## Comandos Disponíveis

Para ver todos os comandos disponíveis:

```bash
make help
```

### Ambiente

- `make install` - Instala dependências do projeto
- `make clean` - Remove arquivos temporários
- `make dev` - Executa em modo desenvolvimento

### Qualidade

- `make test` - Executa testes
- `make coverage` - Gera relatório de cobertura
- `make lint` - Executa linters
- `make format` - Formata código

### Banco de Dados

- `make db-init` - Inicializa banco de dados
- `make db-clean` - Remove banco de dados
- `make db-backup` - Faz backup do banco
- `make logs` - Visualiza logs do banco

### Exemplos

```bash
# Executa o agente com um prompt
make dev prompt-tdd="Cadastro de pessoas" mode=mcp format=markdown

# Visualiza os últimos 20 logs de uma sessão
make logs ARGS="--limit 20 --session abc123"

# Visualiza detalhes de uma execução específica
make logs ARGS="--id 42"
```