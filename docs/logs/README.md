# Logs

O Agent Flow TDD implementa um sistema robusto de logging que permite o monitoramento, a depuração e a análise de todas as operações realizadas pelo framework.

## Conteúdo

Nesta seção, você encontrará informações sobre:

- [Formato](format.md) - Estrutura e formato dos logs
- [CLI](cli.md) - Interface de linha de comando para visualização de logs
- [Níveis](levels.md) - Níveis de severidade e filtragem de logs
- [Armazenamento](storage.md) - Armazenamento e retenção de logs

## Visão Geral

O sistema de logs do Agent Flow TDD opera em dois níveis principais:

1. **Logs de Texto**: Armazenados em arquivos de texto para diagnóstico rápido
2. **Logs Estruturados**: Armazenados em banco de dados SQLite para análise detalhada

## Tipos de Logs

O framework gera diferentes tipos de logs:

- **Logs de Aplicação**: Atividades do sistema, inicialização, erros
- **Logs de Execução**: Detalhes de cada execução de agente
- **Logs de Modelo**: Interações com modelos de IA
- **Logs de Guardrail**: Resultados de validações
- **Logs de Banco de Dados**: Operações no banco de dados

## Componentes do Sistema de Logs

### 1. Logger Principal

Fornece funções para registro de logs em diferentes níveis:

```python
from src.core.logger import get_logger

logger = get_logger(__name__)
logger.info("Operação iniciada")
logger.debug("Detalhe da operação")
logger.error("Erro encontrado", exc_info=True)
```

### 2. Banco de Dados

Armazena logs estruturados para consulta e análise:

```bash
# Visualizar logs recentes
make logs

# Filtrar por sessão
make logs ARGS="--session minha-sessao-123"
```

### 3. Arquivos de Log

Armazenam logs em formato texto:

```
logs/app.log     # Logs da aplicação
logs/error.log   # Erros e exceções
logs/model.log   # Interações com modelos
```

## Comandos Úteis

### Visualização de Logs

```bash
# Visualizar logs recentes via CLI
make logs

# Visualizar logs de erro
tail -f logs/error.log

# Buscar por termo nos logs
grep "ERROR" logs/app.log
```

### Limpeza de Logs

```bash
# Limpar arquivos de log antigos
make clean-logs
```

## Análise de Logs

O sistema de logs foi projetado para facilitar a análise e diagnóstico de problemas:

- **Rastreamento de Contexto**: Cada log inclui informações de contexto
- **Correlação**: IDs de sessão e execução permitem correlacionar eventos
- **Mascaramento**: Dados sensíveis são automaticamente mascarados
- **Formatação**: Logs são formatados para facilitar a leitura 