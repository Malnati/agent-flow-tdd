# Variáveis de Ambiente

O Agent Flow TDD utiliza variáveis de ambiente para configuração. É importante configurá-las corretamente para o funcionamento adequado do sistema.

## Regra Importante

**IMPORTANTE**: O projeto segue uma regra de não utilizar arquivos `.env`. Todas as variáveis de ambiente devem ser configuradas diretamente no ambiente ou passadas como argumentos.

## Variáveis Obrigatórias

Dependendo do contexto de execução, as seguintes variáveis são obrigatórias:

### Contexto CLI

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `OPENAI_API_KEY` | Chave da API da OpenAI (obrigatória para modelos GPT) | `sk-1234567890abcdef...` |

### Contexto GitHub

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `GITHUB_TOKEN` | Token de acesso ao GitHub | `ghp_1234567890abcdef...` |

### Contexto de Publicação

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `PYPI_TOKEN` | Token de acesso ao PyPI | `pypi-1234567890abcdef...` |

## Variáveis Opcionais

Estas variáveis são opcionais e possuem valores padrão:

| Variável | Descrição | Valor Padrão | Exemplo |
|----------|-----------|--------------|---------|
| `DEFAULT_MODEL` | Modelo padrão a ser usado | `tinyllama-1.1b` | `gpt-4-turbo` |
| `ELEVATION_MODEL` | Modelo para fallback | `tinyllama-1.1b` | `gpt-4-turbo` |
| `MAX_RETRIES` | Número máximo de tentativas | `3` | `5` |
| `MODEL_TIMEOUT` | Timeout para chamadas de modelo (segundos) | `120` | `180` |
| `FALLBACK_ENABLED` | Habilita fallback entre modelos | `true` | `false` |
| `CACHE_ENABLED` | Habilita cache de respostas | `true` | `false` |
| `CACHE_TTL` | Tempo de vida do cache (segundos) | `3600` | `7200` |
| `CACHE_DIR` | Diretório para armazenamento de cache | `cache` | `/tmp/cache` |
| `LOG_LEVEL` | Nível de log | `INFO` | `DEBUG` |
| `OPENROUTER_KEY` | Chave da API OpenRouter | - | `sk-or-v1-1234567890abcdef...` |
| `GEMINI_KEY` | Chave da API Google Gemini | - | `AI123456789...` |
| `ANTHROPIC_KEY` | Chave da API Anthropic | - | `sk-ant-1234567890abcdef...` |

## Como Configurar

### Linux/macOS

```bash
# Exportar variáveis no terminal
export OPENAI_API_KEY="sk-1234567890abcdef..."
export DEFAULT_MODEL="gpt-4-turbo"

# OU passar diretamente na linha de comando
OPENAI_API_KEY="sk-1234567890abcdef..." make tdd prompt="Criar API"
```

### Windows

```bash
# Cmd
set OPENAI_API_KEY=sk-1234567890abcdef...
set DEFAULT_MODEL=gpt-4-turbo

# PowerShell
$env:OPENAI_API_KEY="sk-1234567890abcdef..."
$env:DEFAULT_MODEL="gpt-4-turbo"
```

## Verificação

Você pode verificar se as variáveis obrigatórias estão configuradas com:

```bash
make status
```

Este comando mostrará o status de todas as variáveis necessárias para o funcionamento do sistema.

## Dicas de Segurança

- **Nunca** armazene chaves de API em repositórios públicos
- Use variáveis de ambiente temporárias para testes
- Em ambientes de produção, use sistemas de gestão de segredos
- Considere criar chaves com permissões limitadas para maior segurança

## Exemplo Completo

```bash
# Configuração básica
export OPENAI_API_KEY="sk-1234567890abcdef..."
export DEFAULT_MODEL="gpt-4-turbo"

# Configuração avançada
export FALLBACK_ENABLED="true"
export ELEVATION_MODEL="gpt-4-turbo"
export MAX_RETRIES="5"
export MODEL_TIMEOUT="180"
export LOG_LEVEL="DEBUG"

# Executar
make tdd prompt="Criar API REST" format=json
``` 