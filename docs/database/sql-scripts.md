# Scripts SQL

Esta página contém scripts SQL úteis para consulta e manutenção do banco de dados do Agent Flow TDD.

## Consulta de Execuções Recentes

```sql
SELECT 
    id, 
    datetime(timestamp, 'localtime') as date_time, 
    session_id, 
    substr(input, 1, 50) || '...' as input_preview, 
    output_type
FROM 
    agent_runs 
ORDER BY 
    timestamp DESC 
LIMIT 10;
```

## Detalhes de uma Execução Específica

```sql
-- Substitua :run_id pelo ID da execução desejada
SELECT 
    id, 
    datetime(timestamp, 'localtime') as date_time, 
    session_id, 
    input, 
    last_agent, 
    output_type, 
    final_output
FROM 
    agent_runs 
WHERE 
    id = :run_id;
```

## Itens de uma Execução

```sql
-- Substitua :run_id pelo ID da execução desejada
SELECT 
    id, 
    datetime(timestamp, 'localtime') as date_time, 
    item_type, 
    source_agent, 
    target_agent, 
    raw_item
FROM 
    run_items 
WHERE 
    run_id = :run_id 
ORDER BY 
    timestamp;
```

## Resultados de Guardrails

```sql
-- Substitua :run_id pelo ID da execução desejada
SELECT 
    id, 
    datetime(timestamp, 'localtime') as date_time, 
    guardrail_type, 
    results
FROM 
    guardrail_results 
WHERE 
    run_id = :run_id 
ORDER BY 
    timestamp;
```

## Respostas Brutas

```sql
-- Substitua :run_id pelo ID da execução desejada
SELECT 
    id, 
    datetime(timestamp, 'localtime') as date_time, 
    response
FROM 
    raw_responses 
WHERE 
    run_id = :run_id 
ORDER BY 
    timestamp;
```

## Estatísticas de Uso

### Contagem de Execuções por Sessão

```sql
SELECT 
    session_id, 
    COUNT(*) as executions,
    MIN(datetime(timestamp, 'localtime')) as first_execution,
    MAX(datetime(timestamp, 'localtime')) as last_execution
FROM 
    agent_runs 
GROUP BY 
    session_id 
ORDER BY 
    executions DESC;
```

### Contagem de Execuções por Modelo

```sql
SELECT 
    last_agent, 
    COUNT(*) as executions,
    MIN(datetime(timestamp, 'localtime')) as first_execution,
    MAX(datetime(timestamp, 'localtime')) as last_execution
FROM 
    agent_runs 
GROUP BY 
    last_agent 
ORDER BY 
    executions DESC;
```

### Contagem de Execuções por Formato

```sql
SELECT 
    output_type, 
    COUNT(*) as executions
FROM 
    agent_runs 
GROUP BY 
    output_type 
ORDER BY 
    executions DESC;
```

## Manutenção do Banco

### Limpeza de Execuções Antigas

```sql
-- Remove execuções mais antigas que 30 dias
DELETE FROM agent_runs WHERE timestamp < datetime('now', '-30 days');
```

### Limpeza de Cache

```sql
-- Remove cache mais antigo que 24 horas
DELETE FROM model_cache WHERE timestamp < datetime('now', '-1 day');
```

### Vacuum (Otimização do Banco)

```sql
-- Reclama espaço em disco após exclusões
VACUUM;
```

### Verificação de Integridade

```sql
-- Verifica a integridade do banco de dados
PRAGMA integrity_check;
```

## Uso com sqlite3

Você pode executar estes scripts diretamente no banco de dados usando o comando `sqlite3`:

```bash
# Acessa o banco de dados
sqlite3 logs/agent_logs.db

# Dentro do sqlite3, execute os scripts
sqlite> .mode column
sqlite> .headers on
sqlite> SELECT id, datetime(timestamp, 'localtime') as date_time, session_id FROM agent_runs LIMIT 5;
```

## Uso com Python

Você também pode executar estes scripts a partir do Python:

```python
import sqlite3

# Conecta ao banco
conn = sqlite3.connect('logs/agent_logs.db')
conn.row_factory = sqlite3.Row  # Para acessar colunas pelo nome

# Executa uma consulta
cursor = conn.cursor()
cursor.execute("SELECT id, timestamp, session_id FROM agent_runs LIMIT 5")
rows = cursor.fetchall()

# Imprime resultados
for row in rows:
    print(f"ID: {row['id']}, Time: {row['timestamp']}, Session: {row['session_id']}")

# Fecha conexão
conn.close()
``` 