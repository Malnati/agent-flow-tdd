# Formato dos Logs

O Agent Flow TDD utiliza um formato padronizado para os logs, garantindo consistência e facilitando a análise.

## Formato Básico

O formato básico dos logs segue o padrão:

```
TIMESTAMP - NOME_MÓDULO - NÍVEL - MENSAGEM
```

Exemplo:
```
2023-01-01 12:00:00,123 - src.core.agents - INFO - Inicializando agente com modelo gpt-4-turbo
```

## Detalhamento dos Componentes

### Timestamp

O timestamp segue o formato ISO 8601:
```
YYYY-MM-DD HH:MM:SS,mmm
```

Exemplo:
```
2023-01-01 12:00:00,123
```

### Nome do Módulo

O nome do módulo identifica a origem do log:

```
src.core.agents
src.core.models
src.core.db
```

### Nível de Log

Os níveis disponíveis são:

| Nível | Valor | Uso |
|-------|-------|-----|
| `DEBUG` | 10 | Informações detalhadas para diagnóstico |
| `INFO` | 20 | Confirmações de operações normais |
| `WARNING` | 30 | Situações inesperadas mas não críticas |
| `ERROR` | 40 | Erros que impedem uma funcionalidade |
| `CRITICAL` | 50 | Erros críticos que impedem o sistema de funcionar |

### Mensagem

A mensagem do log segue uma estrutura padronizada:

```
TIPO - FUNÇÃO | Detalhe [Dados Adicionais]
```

Exemplos:

```
INÍCIO - execute | Prompt: "Criar API REST"
SUCESSO - validate_input | Validação concluída [status=valid, time=123ms]
FALHA - generate_response | Erro de conexão [model=gpt-4, retry=2/3]
```

## Logs de Execução

Os logs de início/fim de função seguem uma estrutura específica:

### Início de Função

```
INÍCIO - nome_função | Parâmetros: param1=valor1, param2=valor2
```

### Fim de Função

```
FIM - nome_função | Tempo execução: XXms
```

### Erros

```
FALHA - nome_função | Erro: mensagem_erro
```

## Logs de Modelo

Os logs de interação com modelos incluem detalhes específicos:

```
MODEL_REQUEST - nome_modelo | Prompt: "texto" [tokens=123]
MODEL_RESPONSE - nome_modelo | Status: sucesso [tokens=456, time=789ms]
```

## Logs Estruturados (JSON)

Além do formato texto, o sistema suporta logs em formato JSON:

```json
{
  "timestamp": "2023-01-01T12:00:00.123Z",
  "level": "INFO",
  "module": "src.core.agents",
  "function": "execute",
  "message": "Inicializando agente",
  "data": {
    "model": "gpt-4-turbo",
    "prompt_length": 123,
    "session_id": "abc-123"
  }
}
```

## Mascaramento de Dados Sensíveis

O sistema automaticamente mascara dados sensíveis nos logs:

### Padrões Mascarados

- Chaves de API: `sk-1234...`→ `sk-****`
- Tokens: `Bearer eyJhbGciOi...` → `Bearer ***TOKEN***`
- Senhas: `password=secret123` → `password=***`

### Configuração de Mascaramento

O mascaramento é configurado em `src/configs/kernel.yaml`:

```yaml
logging:
  security:
    sensitive_keywords:
      - pass
      - senha
      - password
      - token
      - api_key
    token_patterns:
      - 'sk-[a-zA-Z0-9]{20,}'
      - 'ghp_[a-zA-Z0-9]{20,}'
    masking:
      default_mask: "***"
      prefix_length: 4
```

## Exemplo Completo

```
2023-01-01 12:00:00,123 - src.core.agents - INFO - INÍCIO - execute | Parâmetros: prompt="Criar API REST", format=json
2023-01-01 12:00:00,124 - src.core.models - DEBUG - MODEL_REQUEST - gpt-4-turbo | Tokens: 125
2023-01-01 12:00:01,234 - src.core.models - INFO - MODEL_RESPONSE - gpt-4-turbo | Status: sucesso [tokens=430, time=1110ms]
2023-01-01 12:00:01,235 - src.core.db - DEBUG - DB_WRITE - agent_runs | ID: 123
2023-01-01 12:00:01,236 - src.core.agents - INFO - FIM - execute | Tempo execução: 1113ms
```

## Recomendações para Logging

1. **Seja Específico**: Inclua detalhes suficientes para diagnóstico
2. **Seja Consistente**: Siga o formato padrão
3. **Seja Conciso**: Evite informações desnecessárias
4. **Seja Cuidadoso**: Não logue dados sensíveis ou grandes volumes de texto 