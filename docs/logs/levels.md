# Níveis de Log

O Agent Flow TDD implementa um sistema de logs com diferentes níveis de severidade, permitindo controlar a quantidade e o tipo de informação registrada.

## Níveis Disponíveis

O sistema utiliza os níveis padrão do Python logging, organizados em ordem crescente de severidade:

| Nível | Valor | Descrição | Uso Típico |
|-------|-------|-----------|------------|
| `DEBUG` | 10 | Informações detalhadas | Valores intermediários, variáveis de estado, detalhes de execução |
| `INFO` | 20 | Informações gerais | Eventos normais, início/fim de operações, confirmações |
| `WARNING` | 30 | Avisos | Situações inesperadas, mas não críticas, degradação de performance |
| `ERROR` | 40 | Erros | Falhas em operações específicas, exceções tratadas |
| `CRITICAL` | 50 | Erros críticos | Falhas que impedem o funcionamento do sistema, crash iminente |

## Configuração Global

O nível de log padrão é configurado em `src/configs/kernel.yaml`:

```yaml
logging:
  levels:
    default: INFO
    map:
      DEBUG: 10
      INFO: 20
      WARNING: 30
      ERROR: 40
      CRITICAL: 50
```

## Configuração via Variável de Ambiente

Você pode alterar o nível de log através da variável de ambiente `LOG_LEVEL`:

```bash
# Configurar para nível DEBUG
export LOG_LEVEL=DEBUG

# Executar com nível DEBUG apenas para esta execução
LOG_LEVEL=DEBUG make tdd prompt="Criar API REST"
```

## Uso nos Logs

### Nível DEBUG

```python
logger.debug("Valor recebido: %s", value)
logger.debug(f"Detalhes da operação: {operation_details}")
```

Exemplos de uso:
- Valores intermediários de cálculos
- Estados de flags e variáveis
- Detalhes de requisições e respostas
- Informações de cache

### Nível INFO

```python
logger.info("INÍCIO - %s | Parâmetros: %s", func_name, params)
logger.info(f"FIM - {func_name} | Tempo execução: {time_ms}ms")
```

Exemplos de uso:
- Início e fim de funções importantes
- Eventos de inicialização de componentes
- Carregamento de configurações
- Operações de banco de dados bem-sucedidas

### Nível WARNING

```python
logger.warning("Tentativa %d de %d falhou, tentando novamente", attempt, max_attempts)
logger.warning(f"Recurso {resource_name} próximo do limite ({usage}%)")
```

Exemplos de uso:
- Retry de operações
- Uso elevado de recursos
- Deprecation warnings
- Timeout parcial
- Fallback para modelo alternativo

### Nível ERROR

```python
logger.error("FALHA - %s | Erro: %s", func_name, str(error), exc_info=True)
logger.error(f"Falha ao conectar com serviço {service_name}: {error_message}")
```

Exemplos de uso:
- Exceções capturadas
- Falhas de conexão
- Timeout de operações
- Erros de validação
- Falhas em chamadas de API

### Nível CRITICAL

```python
logger.critical("Sistema incapaz de inicializar: %s", str(error), exc_info=True)
logger.critical(f"Erro fatal no componente {component_name}: {error_message}")
```

Exemplos de uso:
- Falhas fatais na inicialização
- Corrupção de dados
- Falhas de segurança graves
- Condições irrecuperáveis

## Filtragem de Logs

### Via Script

Para visualizar apenas logs de um determinado nível:

```bash
# Mostrar apenas warnings e acima
export LOG_LEVEL=WARNING
make tdd prompt="Criar API"

# Ou via grep nos logs
grep "ERROR" logs/app.log
```

### Via Código

```python
# Configurar o logger para um módulo específico
logger = logging.getLogger("src.core.models")
logger.setLevel(logging.DEBUG)  # Apenas para este logger
```

## Recomendações

### Quando Usar cada Nível

- **DEBUG**: Informações úteis para desenvolvedores durante diagnóstico
- **INFO**: Eventos normais que mostram o progresso da aplicação
- **WARNING**: Situações potencialmente problemáticas que merecem atenção
- **ERROR**: Problemas que impediram uma operação específica
- **CRITICAL**: Problemas severos que podem impedir a continuidade da aplicação

### Boas Práticas

1. **Seja Consistente**: Use o mesmo nível para eventos similares
2. **Inclua Contexto**: Adicione informações suficientes para entender o problema
3. **Use exc_info=True**: Para logs de erro, inclua o stack trace
4. **Evite DEBUG em Produção**: Use DEBUG apenas em ambientes de desenvolvimento
5. **Evite Logging Excessivo**: Não logue dentro de loops com muitas iterações

## Configuração Avançada

### Logging por Componente

É possível configurar níveis diferentes para componentes específicos:

```yaml
logging:
  levels:
    default: INFO
    components:
      "src.core.models": DEBUG
      "src.core.db": WARNING
```

### Customização do Formatter

O formato dos logs pode ser customizado em `src/configs/kernel.yaml`:

```yaml
logging:
  format:
    default: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    debug: "%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s"
``` 