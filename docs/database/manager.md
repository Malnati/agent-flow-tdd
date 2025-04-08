# Gerenciador de Banco de Dados

O Agent Flow TDD utiliza uma classe `DatabaseManager` que centraliza todas as interações com o banco de dados SQLite. Esta página documenta a API disponível para manipulação e consulta do banco.

## Classe DatabaseManager

A classe `DatabaseManager` está localizada em `src/core/db.py` e fornece uma interface completa para interação com o banco de dados.

```python
from src.core.db import DatabaseManager

# Cria uma instância do gerenciador
db = DatabaseManager()
```

## Métodos Principais

### Inicialização

```python
# Criar gerenciador com caminho padrão
db = DatabaseManager()

# Criar gerenciador com caminho personalizado
db = DatabaseManager(db_path="caminho/para/banco.db")
```

### Logging de Execuções

```python
# Registra uma execução completa
run_id = db.log_run(
    session_id="session-123",
    input="Criar uma API REST",
    final_output='{"name": "API REST", ...}',
    output_type="json",
    last_agent="gpt-4-turbo"
)

# Registra um item de execução
db.log_run_item(
    run_id=run_id,
    item_type="MessageOutput",
    raw_item='{"content": "Hello world"}',
    source_agent="InputGuardrail",
    target_agent="OutputGuardrail"
)

# Registra resultado de guardrail
db.log_guardrail_result(
    run_id=run_id,
    guardrail_type="input",
    results='{"status": "success", "validations": [...]}'
)

# Registra resposta bruta do modelo
db.log_raw_response(
    run_id=run_id,
    response='{"choices": [{"message": {"content": "..."}}]}'
)
```

### Consultas

```python
# Obtém histórico de execuções
history = db.get_run_history(limit=10)

# Obtém detalhes de uma execução específica
run = db.get_run_details(run_id=123)

# Obtém itens de uma execução
items = db.get_run_items(run_id=123)

# Obtém resultados de guardrails de uma execução
guardrails = db.get_guardrail_results(run_id=123)

# Obtém respostas brutas de uma execução
responses = db.get_raw_responses(run_id=123)
```

### Cache de Modelos

```python
# Verifica se há cache disponível
cached_response = db.get_cache(
    cache_key="hash-do-prompt",
    max_age_seconds=3600  # 1 hora
)

# Armazena resposta no cache
db.set_cache(
    cache_key="hash-do-prompt",
    response='{"content": "..."}',
    metadata='{"model": "gpt-4", "timestamp": "..."}'
)

# Limpa cache antigo
db.clean_cache(max_age_seconds=86400)  # 24 horas
```

### Manutenção

```python
# Limpa execuções antigas
db.clean_old_runs(max_age_days=30)

# Otimiza o banco de dados
db.optimize()

# Verifica a integridade do banco
is_valid = db.check_integrity()

# Cria backup do banco
db.backup("backups/backup_2023-01-01.db")
```

## Exemplo Completo

```python
from src.core.db import DatabaseManager

# Cria gerenciador
db = DatabaseManager()

# Registra execução
run_id = db.log_run(
    session_id="demo-session",
    input="Criar um sistema de login",
    final_output='{"name": "Sistema de Login", "description": "..."}',
    output_type="json",
    last_agent="gpt-4-turbo"
)

# Registra itens associados
db.log_run_item(
    run_id=run_id,
    item_type="MessageOutput",
    raw_item='{"content": "..."}',
    source_agent="InputGuardrail",
    target_agent="Agent"
)

db.log_guardrail_result(
    run_id=run_id,
    guardrail_type="input",
    results='{"status": "success"}'
)

# Consulta histórico
history = db.get_run_history(limit=5)
for run in history:
    print(f"Run ID: {run['id']}")
    print(f"Session: {run['session_id']}")
    print(f"Input: {run['input'][:50]}...")
    print(f"Output Type: {run['output_type']}")
    print("---")

# Obtém detalhes da execução
run_details = db.get_run_details(run_id=run_id)
print(f"Full output: {run_details['final_output']}")
```

## Tratamento de Erros

O `DatabaseManager` inclui tratamento interno de erros para evitar falhas críticas no sistema. Todos os métodos registram logs detalhados em caso de erro.

```python
try:
    db.log_run(...)
except Exception as e:
    print(f"Erro ao registrar execução: {str(e)}")
```

## Configurações Avançadas

### Alterando o Schema

Se você precisar modificar o schema do banco, considere criar uma migração usando o método `_execute_schema_update`:

```python
new_schema = """
    CREATE TABLE IF NOT EXISTS my_new_table (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    );
"""

db._execute_schema_update(new_schema)
```

### Conexões Personalizadas

Você pode obter uma conexão direta com o banco para consultas personalizadas:

```python
conn = db.get_connection()
try:
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM agent_runs")
    count = cursor.fetchone()[0]
    print(f"Total de execuções: {count}")
finally:
    conn.close()
``` 