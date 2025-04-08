# Estrutura do Banco de Dados

O banco de dados do Agent Flow TDD utiliza SQLite como sistema de gerenciamento e segue um esquema relacional projetado para armazenar logs estruturados e histórico de execuções.

## Diagrama de Entidade-Relacionamento

```
┌────────────────┐        ┌────────────────┐        ┌────────────────┐
│  agent_runs    │        │   run_items    │        │ guardrail_results
│────────────────│        │────────────────│        │────────────────│
│ id (PK)        │        │ id (PK)        │        │ id (PK)        │
│ timestamp      │        │ run_id (FK)    │────┐   │ run_id (FK)    │────┐
│ session_id     │    ┌───│ timestamp      │    │   │ timestamp      │    │
│ input          │    │   │ item_type      │    │   │ guardrail_type │    │
│ last_agent     │◄───┼───│ raw_item       │    │   │ results        │    │
│ output_type    │    │   │ source_agent   │    │   └────────────────┘    │
│ final_output   │    │   │ target_agent   │    │                         │
└────────────────┘    │   └────────────────┘    │   ┌────────────────┐    │
                      │                         │   │  raw_responses │    │
                      │   ┌────────────────┐    │   │────────────────│    │
                      │   │  model_cache   │    │   │ id (PK)        │    │
                      │   │────────────────│    │   │ run_id (FK)    │────┘
                      │   │ id (PK)        │    │   │ timestamp      │
                      │   │ cache_key      │    │   │ response       │
                      │   │ response       │    │   └────────────────┘
                      │   │ metadata       │    │
                      │   │ timestamp      │    │
                      │   └────────────────┘    │
                      │                         │
                      └─────────────────────────┘
```

## Tabelas

### `agent_runs`

Armazena informações sobre cada execução do agente.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | INTEGER PRIMARY KEY | Identificador único da execução |
| `timestamp` | DATETIME | Data e hora da execução |
| `session_id` | TEXT | Identificador da sessão |
| `input` | TEXT | Prompt de entrada do usuário |
| `last_agent` | TEXT | Último agente executado |
| `output_type` | TEXT | Formato de saída (json, markdown, text) |
| `final_output` | TEXT | Saída final gerada |

### `run_items`

Armazena itens intermediários gerados durante a execução.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | INTEGER PRIMARY KEY | Identificador único do item |
| `run_id` | INTEGER | Referência à execução (FK para agent_runs.id) |
| `timestamp` | DATETIME | Data e hora do item |
| `item_type` | TEXT | Tipo do item (MessageOutput, HandoffCall, etc.) |
| `raw_item` | TEXT | Conteúdo do item em formato JSON |
| `source_agent` | TEXT | Agente que gerou o item |
| `target_agent` | TEXT | Agente destinatário do item |

### `guardrail_results`

Armazena resultados de validações de guardrails.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | INTEGER PRIMARY KEY | Identificador único do resultado |
| `run_id` | INTEGER | Referência à execução (FK para agent_runs.id) |
| `timestamp` | DATETIME | Data e hora da validação |
| `guardrail_type` | TEXT | Tipo de guardrail (input, output) |
| `results` | TEXT | Resultados da validação em formato JSON |

### `raw_responses`

Armazena respostas brutas dos modelos.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | INTEGER PRIMARY KEY | Identificador único da resposta |
| `run_id` | INTEGER | Referência à execução (FK para agent_runs.id) |
| `timestamp` | DATETIME | Data e hora da resposta |
| `response` | TEXT | Resposta bruta do modelo |

### `model_cache`

Armazena cache de respostas dos modelos.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | INTEGER PRIMARY KEY | Identificador único do cache |
| `cache_key` | TEXT | Chave de cache (hash do prompt) |
| `response` | TEXT | Resposta cacheada |
| `metadata` | TEXT | Metadados sobre o cache |
| `timestamp` | DATETIME | Data e hora do cache |

## Índices

- `idx_agent_runs_session`: Índice em `agent_runs.session_id`
- `idx_run_items_run_id`: Índice em `run_items.run_id`
- `idx_guardrail_results_run_id`: Índice em `guardrail_results.run_id`
- `idx_raw_responses_run_id`: Índice em `raw_responses.run_id`
- `idx_cache_key`: Índice único em `model_cache.cache_key`

## Chaves Estrangeiras

- `run_items.run_id` → `agent_runs.id`
- `guardrail_results.run_id` → `agent_runs.id`
- `raw_responses.run_id` → `agent_runs.id`

## Constraints

- `guardrail_type` em `guardrail_results` limitado a 'input' ou 'output'

## Inicialização do Schema

O schema do banco de dados é inicializado automaticamente na primeira execução do sistema ou quando o comando `make db-init` é executado. O DatabaseManager verifica a existência das tabelas e as cria se necessário. 