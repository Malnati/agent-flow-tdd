# Armazenamento de Logs

O Agent Flow TDD utiliza um sistema dual de armazenamento de logs, combinando arquivos de texto para diagnóstico rápido e um banco de dados SQLite para análise estruturada.

## Estrutura de Armazenamento

### Localização dos Logs

Por padrão, todos os logs são armazenados no diretório `logs/` na raiz do projeto:

```
logs/
  ├── app.log           # Logs gerais da aplicação
  ├── error.log         # Apenas erros e avisos críticos
  ├── model.log         # Interações com modelos de IA
  ├── agent_logs.db     # Banco de dados SQLite com logs estruturados
  └── mcp/              # Logs específicos do protocolo MCP
       ├── mcp_pipe.log    # Canal de entrada para mensagens MCP
       └── mcp_output.log  # Canal de saída para respostas MCP
```

### Logs de Texto

Os logs de texto são escritos em arquivos `.log` usando o sistema de logging do Python:

- **app.log**: Todos os logs (INFO e acima)
- **error.log**: Apenas logs de erro (ERROR e CRITICAL)
- **model.log**: Logs específicos de interações com modelos de IA

### Logs Estruturados (SQLite)

O arquivo `agent_logs.db` contém os logs estruturados em formato SQLite, com as seguintes tabelas:

- **agent_runs**: Execuções do agente
- **run_items**: Itens gerados durante execuções
- **guardrail_results**: Resultados de validações
- **raw_responses**: Respostas brutas dos modelos
- **model_cache**: Cache de respostas

## Rotação de Logs

### Logs de Texto

O sistema implementa rotação automática de logs para evitar arquivos excessivamente grandes:

```yaml
# Configuração em src/configs/kernel.yaml
logging:
  rotation:
    max_size: 10485760  # 10MB
    backup_count: 5     # Manter 5 backups
    encoding: "utf-8"
```

Quando um arquivo de log atinge o tamanho máximo:
1. O arquivo atual é renomeado para `app.log.1`
2. Arquivos existentes são incrementados (`app.log.1` → `app.log.2`, etc.)
3. Um novo arquivo vazio `app.log` é criado
4. Arquivos além do `backup_count` são removidos

### Logs de Banco de Dados

O banco de dados não implementa rotação automática, mas oferece comandos para limpeza:

```bash
# Limpar logs mais antigos que 30 dias
make db-clean-old ARGS="--days 30"

# Limpar cache mais antigo que 24 horas
make db-clean-cache ARGS="--hours 24"
```

## Retenção de Logs

### Política de Retenção Padrão

Por padrão, o sistema mantém:

- **Logs de Texto**: 5 arquivos rotacionados (configurável)
- **Logs de Banco**: Sem limite de tempo (requer limpeza manual)

### Configuração de Retenção

Você pode configurar políticas de retenção em `src/configs/kernel.yaml`:

```yaml
logging:
  retention:
    text_logs_days: 30      # Manter logs de texto por 30 dias
    db_logs_days: 90        # Manter logs de banco por 90 dias
    auto_cleanup: true      # Habilitar limpeza automática
    cleanup_interval: 86400 # Intervalo de limpeza (1 dia)
```

### Limpeza Manual

Para limpar logs manualmente:

```bash
# Remover arquivos de log antigos
find logs/ -name "*.log.*" -mtime +30 -delete

# Limpar logs do banco de dados
make db-clean-old ARGS="--days 30"
```

## Backup de Logs

### Backup Automático

O sistema pode ser configurado para criar backups periódicos:

```yaml
logging:
  backup:
    enabled: true
    interval: 604800  # 7 dias
    destination: "backups/logs/"
    compress: true
```

### Backup Manual

Para backup manual:

```bash
# Backup de logs de texto
mkdir -p backups/logs/$(date +%Y%m%d)
cp logs/*.log backups/logs/$(date +%Y%m%d)/

# Backup do banco de dados
make db-backup
```

## Formatos de Arquivo

### Logs de Texto

Os logs de texto são armazenados em formato UTF-8 com a estrutura:

```
TIMESTAMP - NOME_MÓDULO - NÍVEL - MENSAGEM
```

Exemplo:
```
2023-01-01 12:00:00,123 - src.core.agents - INFO - INÍCIO - execute | Parâmetros: prompt="Criar API REST"
```

### Logs de Banco de Dados

Os logs do banco de dados são armazenados em tabelas SQLite, seguindo o schema definido na seção de [Banco de Dados](../database/structure.md).

## Monitoramento de Uso de Disco

### Verificação de Espaço

Para verificar o uso de espaço pelos logs:

```bash
# Tamanho total do diretório de logs
du -sh logs/

# Tamanho dos arquivos individuais
ls -lh logs/

# Tamanho do banco de dados
ls -lh logs/agent_logs.db
```

### Alerta de Espaço

O sistema pode ser configurado para alertar quando o espaço de logs ultrapassar um limite:

```yaml
logging:
  storage:
    max_size_mb: 1000    # 1GB
    alert_threshold: 0.8 # Alertar quando atingir 80%
    alert_action: "warn" # Apenas avisar (outras opções: "rotate", "clean")
```

## Considerações de Segurança

### Mascaramento de Dados Sensíveis

Todos os logs passam por um processo de mascaramento para remover informações sensíveis:

- Chaves de API
- Tokens de autenticação
- Senhas
- Informações pessoais

### Permissões de Arquivo

Para garantir a segurança dos logs:

```bash
# Configurar permissões restritas
chmod 750 logs/
chmod 640 logs/*.log
chmod 640 logs/agent_logs.db
```

### Criptografia

Para ambientes de alta segurança, considere a criptografia dos logs:

```bash
# Exemplo com SQLCipher (requer instalação)
sqlcipher logs/agent_logs.db
``` 