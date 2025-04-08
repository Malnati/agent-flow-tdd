# Comandos Makefile para Banco de Dados

O Agent Flow TDD fornece uma série de comandos Makefile para facilitar operações comuns no banco de dados, permitindo uma manutenção simplificada sem necessidade de conhecimentos avançados em SQL.

## Inicialização do Banco

```bash
make db-init
```

Este comando:
- Cria o diretório `logs/` se não existir
- Inicializa o banco de dados SQLite em `logs/agent_logs.db`
- Cria todas as tabelas conforme o schema definido em `src/core/db.py`
- Define os índices e constraints necessários

Exemplo de saída:
```
🗄️ Inicializando banco de dados...
✅ Banco de dados inicializado!
```

## Limpeza do Banco

```bash
make db-clean
```

Este comando:
- Remove o arquivo do banco de dados em `logs/agent_logs.db`
- Não afeta outros arquivos de log

⚠️ **Atenção**: Esta operação é irreversível. Considere fazer um backup antes.

Exemplo de saída:
```
🧹 Limpando banco de dados...
✅ Banco de dados removido!
```

## Backup do Banco

```bash
make db-backup
```

Este comando:
- Cria o diretório `backups/` se não existir
- Faz uma cópia do banco atual com um timestamp no nome
- Mantém o banco original intacto

Exemplo de saída:
```
💾 Criando backup do banco de dados...
✅ Backup criado em backups/agent_logs_20230101_120000.db
```

## Visualização de Logs

```bash
make logs [ARGS="<argumentos>"]
```

Este comando:
- Executa o script `src/scripts/utils_view_logs.py`
- Exibe os logs armazenados no banco de forma formatada
- Suporta diversos parâmetros para filtragem e formatação

### Parâmetros Suportados

| Parâmetro | Descrição | Exemplo |
|-----------|-----------|---------|
| `--limit N` | Limita a quantidade de logs exibidos | `--limit 20` |
| `--session ID` | Filtra por ID de sessão | `--session abc123` |
| `--id N` | Mostra detalhes de uma execução específica | `--id 42` |
| `--format FMT` | Formato de saída (text, json) | `--format json` |
| `--agent NAME` | Filtra por nome do agente | `--agent gpt-4` |
| `--output TYPE` | Filtra por tipo de saída | `--output markdown` |
| `--date YYYY-MM-DD` | Filtra por data | `--date 2023-01-01` |

### Exemplos de Uso

```bash
# Últimos 10 logs (padrão)
make logs

# Últimos 20 logs
make logs ARGS="--limit 20"

# Logs de uma sessão específica
make logs ARGS="--session minha-sessao-123"

# Detalhes de uma execução específica
make logs ARGS="--id 42"

# Logs de execuções que usaram um modelo específico
make logs ARGS="--agent gpt-4-turbo"

# Combinar múltiplos filtros
make logs ARGS="--limit 15 --agent gpt-4-turbo --output markdown"
```

## Otimização do Banco

```bash
make db-optimize
```

Este comando:
- Remove registros antigos conforme configuração
- Executa VACUUM para recuperar espaço em disco
- Atualiza estatísticas para consultas mais eficientes

## Backup Automático

O Agent Flow TDD também suporta backups automáticos através de cron jobs. Para configurar, adicione o seguinte ao seu crontab:

```bash
# Backup diário às 2 da manhã
0 2 * * * cd /caminho/para/agent-flow-tdd && make db-backup > /dev/null 2>&1
```

## Execução de Consultas Customizadas

Para executar consultas SQL personalizadas:

```bash
# Acessa o shell SQLite
sqlite3 logs/agent_logs.db

# Ou execute um comando específico
echo "SELECT COUNT(*) FROM agent_runs;" | sqlite3 logs/agent_logs.db
```

## Solução de Problemas

### Erro de Permissão

Se encontrar erros de permissão ao executar os comandos:

```bash
# Verifica as permissões do diretório logs/
ls -la logs/

# Corrige as permissões se necessário
chmod -R 755 logs/
chmod 644 logs/agent_logs.db
```

### Banco Corrompido

Se o banco estiver corrompido:

```bash
# Verifica a integridade
echo "PRAGMA integrity_check;" | sqlite3 logs/agent_logs.db

# Se corrompido, restaure um backup
make db-clean
cp backups/ultimo_backup.db logs/agent_logs.db
``` 