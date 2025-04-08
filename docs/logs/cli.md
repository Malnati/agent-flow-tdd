# CLI de Logs

O Agent Flow TDD inclui uma interface de linha de comando (CLI) dedicada à visualização e análise de logs, permitindo consultar facilmente o histórico de execuções do sistema.

## Comando Básico

O comando básico para acessar a CLI de logs é:

```bash
make logs [ARGS="<argumentos>"]
```

Este comando executa o script `src/scripts/utils_view_logs.py` e exibe os logs armazenados no banco de dados SQLite.

## Parâmetros

A CLI de logs suporta diversos parâmetros para filtragem e formatação:

| Parâmetro | Descrição | Valor Padrão | Exemplo |
|-----------|-----------|--------------|---------|
| `--limit` | Número máximo de logs a exibir | 10 | `--limit 20` |
| `--session` | Filtrar por ID de sessão | *(todos)* | `--session abc123` |
| `--id` | Mostrar detalhes de uma execução específica | *(nenhum)* | `--id 42` |
| `--format` | Formato de saída | `text` | `--format json` |
| `--agent` | Filtrar pelo modelo usado | *(todos)* | `--agent gpt-4` |
| `--output` | Filtrar por tipo de saída | *(todos)* | `--output markdown` |
| `--date` | Filtrar por data | *(todos)* | `--date 2023-01-01` |
| `--type` | Filtrar por tipo de item | *(todos)* | `--type guardrail` |
| `--full` | Mostrar conteúdo completo | `false` | `--full` |
| `--no-color` | Desabilitar cores na saída | `false` | `--no-color` |

## Exemplos de Uso

### Visualização Básica

```bash
# Exibe os últimos 10 logs (padrão)
make logs
```

Saída:
```
📋 Últimos 10 logs:
┌────┬─────────────────────┬───────────────┬────────────────────────────┬───────────┐
│ ID │ Data                │ Sessão        │ Prompt                     │ Formato   │
├────┼─────────────────────┼───────────────┼────────────────────────────┼───────────┤
│ 42 │ 2023-01-01 12:00:00 │ session-123   │ Criar uma API REST         │ json      │
│ 41 │ 2023-01-01 11:30:00 │ session-123   │ Sistema de autenticação    │ markdown  │
│ 40 │ 2023-01-01 11:00:00 │ session-456   │ Cadastro de usuários       │ json      │
│ ... │
└────┴─────────────────────┴───────────────┴────────────────────────────┴───────────┘
```

### Filtrar por Sessão

```bash
# Exibe logs de uma sessão específica
make logs ARGS="--session session-123"
```

### Exibir Detalhes de uma Execução

```bash
# Exibe detalhes completos de uma execução específica
make logs ARGS="--id 42"
```

Saída:
```
📋 Detalhes da execução #42:

📝 Informações Gerais:
- Data: 2023-01-01 12:00:00
- Sessão: session-123
- Modelo: gpt-4-turbo
- Formato: json

📥 Prompt:
Criar uma API REST para um sistema de e-commerce

📤 Saída Final:
{
  "name": "API REST para E-commerce",
  "description": "API REST completa para um sistema de e-commerce...",
  "acceptance_criteria": [
    "A API deve ter endpoints para CRUD de produtos",
    ...
  ]
}

🛡️ Guardrails (2):
- input: Sucesso (validações: 5, status: válido)
- output: Sucesso (validações: 3, status: válido)

🔄 Itens (4):
- MessageOutput: De InputGuardrail para Agent (12:00:00)
- HandoffCall: De Agent para OutputGuardrail (12:00:01)
- MessageOutput: De OutputGuardrail para Agent (12:00:02)
- FinalOutput: De Agent para CLI (12:00:03)

🤖 Respostas do Modelo (2):
- gpt-4-turbo: 12:00:01 (tokens: 230)
- gpt-4-turbo: 12:00:02 (tokens: 180)
```

### Formatação Personalizada

```bash
# Exibe logs em formato JSON
make logs ARGS="--format json --limit 5"
```

Saída:
```json
[
  {
    "id": 42,
    "timestamp": "2023-01-01T12:00:00Z",
    "session_id": "session-123",
    "input": "Criar uma API REST",
    "last_agent": "gpt-4-turbo",
    "output_type": "json",
    "final_output": "..."
  },
  ...
]
```

### Combinação de Filtros

```bash
# Combina múltiplos filtros
make logs ARGS="--agent gpt-4-turbo --output markdown --limit 15"
```

## Visualização Detalhada

### Conteúdo Completo

Para ver o conteúdo completo (sem truncamento):

```bash
make logs ARGS="--id 42 --full"
```

### Desativar Cores

Para saída sem cores (útil para redirecionamento):

```bash
make logs ARGS="--no-color > logs_export.txt"
```

## Logs de Dia Específico

```bash
# Logs de um dia específico
make logs ARGS="--date 2023-01-01"

# Logs de hoje
make logs ARGS="--date today"

# Logs de ontem
make logs ARGS="--date yesterday"
```

## Exportação de Logs

### Exportar para Arquivo

```bash
# Exportar para arquivo texto
make logs ARGS="--limit 100" > logs_export.txt

# Exportar para JSON
make logs ARGS="--format json --limit 100" > logs_export.json
```

### Exportar para CSV

```bash
# Usar com o comando cut para formato CSV
make logs ARGS="--format plain --limit 100" | cut -d'|' -f1-5 > logs_export.csv
```

## Integração com Outras Ferramentas

### Filtrar com Grep

```bash
# Filtrar ainda mais a saída com grep
make logs ARGS="--limit 100" | grep "ERROR"
```

### Usar com JQ (para JSON)

```bash
# Exportar como JSON e processar com jq
make logs ARGS="--format json --limit 100" | jq '.[] | {id, session_id, timestamp}'
```

## Solução de Problemas

Se encontrar problemas ao usar a CLI de logs:

1. **Verifique o banco de dados**: `make db-check`
2. **Reinicie o banco se necessário**: `make db-init`
3. **Verifique permissões de arquivos**: `ls -la logs/` 