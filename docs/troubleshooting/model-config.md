# Configuração de Modelos

Este guia contém informações detalhadas sobre como configurar corretamente os diferentes modelos de IA suportados no Agent Flow TDD e resolver problemas específicos de cada um.

## Modelos Locais

### TinyLLaMA (1.1B)

O TinyLLaMA é um modelo pequeno e rápido, ideal para desenvolvimento e testes.

**Configuração Básica:**
```bash
# Uso básico
make tdd prompt="Criar uma API REST" model=tinyllama-1.1b

# Com parâmetros personalizados
make tdd prompt="Criar uma API REST" model=tinyllama-1.1b ARGS="--temperature 0.7 --max_tokens 2048"
```

**Requisitos:**
- Mínimo: 2GB de RAM
- Armazenamento: ~1GB para os arquivos do modelo

**Resolução de Problemas:**
- **Lentidão:** Ajuste o número de threads para corresponder ao número de núcleos do CPU:
  ```bash
  export LLAMA_NUM_THREADS=4
  ```
- **Erros de Geração:** Reduza a temperatura:
  ```bash
  make tdd prompt="Criar API" model=tinyllama-1.1b ARGS="--temperature 0.3"
  ```

### Phi-1/Phi-2 (1.3B/2.7B)

Os modelos Phi da Microsoft oferecem bom equilíbrio entre tamanho e capacidade.

**Configuração Básica:**
```bash
# Phi-1 (1.3B)
make tdd prompt="Criar uma API REST" model=phi1

# Phi-2 (2.7B)
make tdd prompt="Criar uma API REST" model=phi2
```

**Requisitos:**
- Phi-1: 3GB de RAM
- Phi-2: 6GB de RAM
- Armazenamento: 1.5GB (Phi-1) ou 3GB (Phi-2)

**Resolução de Problemas:**
- **Erros de Formato na Saída:** Use argumentos para controlar o formato:
  ```bash
  make tdd prompt="Criar API" model=phi2 format=markdown
  ```
- **Erros de Carregamento:** Verificar formato do modelo:
  ```bash
  ls -la models/phi-2.Q4_K_M.gguf
  make download-model model=phi2  # Re-baixar se necessário
  ```

### DeepSeek Coder (6.7B)

O DeepSeek Coder é especializado em geração de código com maior precisão.

**Configuração Básica:**
```bash
# Uso padrão
make tdd prompt="Criar uma API REST" model=deepseek_local

# Com formato específico
make tdd prompt="Criar uma API REST" model=deepseek_local format=json
```

**Requisitos:**
- Mínimo: 12GB de RAM
- Recomendado: GPU com 8GB+ VRAM
- Armazenamento: ~4GB para os arquivos do modelo

**Resolução de Problemas:**
- **Erro `CUDA out of memory`:** Reduza as camadas na GPU:
  ```bash
  export LLAMA_N_GPU_LAYERS=20
  ```
- **Lentidão extrema:** Use quantização mais agressiva:
  ```bash
  # Baixar versão com quantização mais agressiva
  make download-model model=deepseek_local quant=Q3_K_S
  ```
- **Resultados incompletos:** Aumente o contexto e tokens:
  ```bash
  make tdd prompt="Criar API" model=deepseek_local ARGS="--max_tokens 4096 --context_length 8192"
  ```

## Modelos Remotos (API)

### GPT-4/GPT-3.5 (OpenAI)

**Configuração Básica:**
```bash
# GPT-4
make tdd prompt="Criar uma API REST" model=gpt-4-turbo

# GPT-3.5
make tdd prompt="Criar uma API REST" model=gpt-3.5-turbo
```

**Requisitos:**
- Chave de API válida da OpenAI
- Conexão estável com a internet

**Resolução de Problemas:**
- **Erro de Autenticação:**
  ```bash
  # Verificar se a chave está configurada
  echo $OPENAI_API_KEY
  
  # Configurar a chave
  export OPENAI_API_KEY="sua-chave-aqui"
  ```
- **Erros de Rate Limit:**
  ```bash
  # Adicionar delay entre requisições
  export OPENAI_REQUEST_DELAY=2  # em segundos
  
  # Ou usar modelo de fallback
  export FALLBACK_MODEL=phi2
  ```
- **Timeout nas Requisições:**
  ```bash
  # Aumentar timeout
  export MODEL_TIMEOUT=180  # em segundos
  ```

### Claude (Anthropic)

**Configuração Básica:**
```bash
# Claude 3 Opus
make tdd prompt="Criar uma API REST" model=claude-3-opus

# Claude 3 Sonnet
make tdd prompt="Criar uma API REST" model=claude-3-sonnet
```

**Requisitos:**
- Chave de API válida da Anthropic
- Conexão estável com a internet

**Resolução de Problemas:**
- **Erro de Autenticação:**
  ```bash
  # Verificar se a chave está configurada
  echo $ANTHROPIC_API_KEY
  
  # Configurar a chave
  export ANTHROPIC_API_KEY="sua-chave-aqui"
  ```
- **Problemas com a Saída:**
  ```bash
  # Ajustar sistema de prompt
  export CLAUDE_SYSTEM_PROMPT="Você é um assistente de programação que fornece código claro e bem comentado."
  ```

## Configuração do Mecanismo de Fallback

O Agent Flow TDD inclui um sistema de fallback que permite mudar automaticamente para outro modelo quando o principal falha.

**Configuração Básica:**
```bash
# Configurar modelo de fallback
export FALLBACK_MODEL=phi2  # Modelo para usar se o principal falhar

# Configurar prioridade de fallback (ordem de tentativa)
export FALLBACK_PRIORITY="gpt-4-turbo,claude-3-sonnet,phi2,tinyllama-1.1b"
```

**Sintomas e Soluções para Problemas de Fallback:**
- **Fallback não ocorre:** Verifique se o timeout está configurado:
  ```bash
  export MODEL_TIMEOUT=60  # Tempo limite antes de acionar fallback
  ```
- **Fallback para modelo incorreto:** Verifique a ordem de prioridade:
  ```bash
  export FALLBACK_PRIORITY="modelo1,modelo2,modelo3"
  ```
- **Erros repetidos mesmo com fallback:** Verifique disponibilidade dos modelos:
  ```bash
  make status  # Verificar quais modelos estão disponíveis
  make test-models  # Testar todos os modelos configurados
  ```

## Otimização de Desempenho

### Para Modelos Locais

```bash
# Otimização para CPU
export LLAMA_NUM_THREADS=$(nproc)  # Linux
export LLAMA_NUM_THREADS=$(sysctl -n hw.ncpu)  # macOS

# Otimização para GPU
export LLAMA_CUDA_DEVICE=0  # ID da GPU
export LLAMA_N_GPU_LAYERS=-1  # -1 para todas as camadas na GPU

# Otimização para macOS (Apple Silicon)
export LLAMA_METAL_DEVICE=0
```

### Para Modelos de API

```bash
# Paralelismo para múltiplas requisições
export MAX_CONCURRENT_REQUESTS=3

# Cache para economizar chamadas
export ENABLE_MODEL_CACHE=1
export CACHE_TTL=3600  # Tempo em segundos
```

## Teste de Configuração

Para verificar se sua configuração está correta:

```bash
# Verificar status de todos os modelos
make status

# Teste rápido com um modelo específico
make test-model model=phi2

# Benchmark de velocidade
make benchmark model=tinyllama-1.1b
``` 