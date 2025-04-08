# Erros Comuns

Esta página contém soluções para os erros mais frequentes encontrados ao usar o Agent Flow TDD.

## Erros de Instalação

### Erro: `ImportError: No module named 'src'`

**Problema**: O Python não consegue encontrar o módulo `src`.

**Solução**:
```bash
# Instalar em modo desenvolvimento
pip install -e .

# OU adicionar o diretório atual ao PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)
```

### Erro: `ModuleNotFoundError: No module named 'llama_cpp'`

**Problema**: A biblioteca llama_cpp não está instalada ou não foi compilada corretamente.

**Solução**:
```bash
# Reinstalar com suporte específico para o SO
pip uninstall -y llama-cpp-python
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python  # Para CUDA
CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python   # Para macOS com Metal
```

### Erro: `error: could not create '/usr/local/lib/python3.13/site-packages': Permission denied`

**Problema**: Falta de permissão para instalar pacotes globalmente.

**Solução**:
```bash
# Usar ambiente virtual
python -m venv .venv
source .venv/bin/activate
pip install -e .

# OU instalar localmente para o usuário
pip install --user -e .
```

## Erros de Modelo

### Erro: `Error loading model: [model_path]`

**Problema**: O modelo não foi encontrado ou está corrompido.

**Solução**:
```bash
# Verificar se o modelo existe
ls -l models/

# Rebaixar o modelo
make download-model
```

### Erro: `Model does not exist: [model_name]`

**Problema**: O modelo solicitado não existe ou não está disponível.

**Solução**:
```bash
# Listar modelos disponíveis
make status

# Usar um modelo diferente
make tdd prompt="Criar API" model=tinyllama-1.1b  # Modelo local
```

### Erro: `InvalidRequestError: You exceeded your current quota`

**Problema**: Limite de quota da API OpenAI excedido.

**Solução**:
```bash
# Verificar saldo e limites no dashboard da OpenAI
# Usar modelo local como alternativa
make tdd prompt="Criar API" model=tinyllama-1.1b
```

## Erros de Ambiente

### Erro: `Error: OPENAI_API_KEY environment variable not set`

**Problema**: Variável de ambiente obrigatória não configurada.

**Solução**:
```bash
# Configurar a variável de ambiente
export OPENAI_API_KEY="sua-chave-aqui"

# OU passar diretamente na linha de comando
OPENAI_API_KEY="sua-chave-aqui" make tdd prompt="Criar API"
```

### Erro: `AssertionError: Python 3.13 or higher is required`

**Problema**: Versão do Python incompatível.

**Solução**:
```bash
# Verificar versão do Python
python --version

# Instalar versão compatível e configurar ambiente
pyenv install 3.13.0
pyenv local 3.13.0
make install
```

## Erros de Banco de Dados

### Erro: `sqlite3.OperationalError: database is locked`

**Problema**: Banco de dados bloqueado por outro processo.

**Solução**:
```bash
# Verificar processos que estão usando o banco
lsof logs/agent_logs.db

# Aguardar liberação ou reiniciar
kill <PID>  # Terminar processo, se necessário
make db-init
```

### Erro: `sqlite3.OperationalError: no such table: agent_runs`

**Problema**: Tabela não encontrada no banco de dados.

**Solução**:
```bash
# Reinicializar o banco de dados
make db-init
```

## Erros de Execução

### Erro: `KeyboardInterrupt: Execution interrupted by user`

**Problema**: Execução interrompida pelo usuário (Ctrl+C).

**Solução**:
```bash
# Reiniciar o comando com timeout menor
make tdd prompt="Criar API" ARGS="--timeout 30"
```

### Erro: `TimeoutError: Model response took too long`

**Problema**: Resposta do modelo levou mais tempo que o limite configurado.

**Solução**:
```bash
# Aumentar o timeout
export MODEL_TIMEOUT=180
make tdd prompt="Criar API"

# OU usar um modelo mais rápido
make tdd prompt="Criar API" model=tinyllama-1.1b
```

### Erro: `JSONDecodeError: Expecting value: line 1 column 1`

**Problema**: Resposta do modelo não é um JSON válido.

**Solução**:
```bash
# Tentar com outro formato
make tdd prompt="Criar API" format=markdown

# OU usar um modelo diferente
make tdd prompt="Criar API" model=gpt-4-turbo
```

## Erros de Rede

### Erro: `ConnectionError: Connection refused`

**Problema**: Falha na conexão com o serviço remoto.

**Solução**:
```bash
# Verificar conectividade
ping api.openai.com

# Verificar proxy/firewall
export HTTP_PROXY="http://proxy:port"
export HTTPS_PROXY="http://proxy:port"
```

### Erro: `SSLError: HTTPSConnectionPool: Max retries exceeded`

**Problema**: Falha de SSL ou número máximo de tentativas excedido.

**Solução**:
```bash
# Aumentar o número de tentativas
export MAX_RETRIES=5
make tdd prompt="Criar API"

# Verificar certificados SSL
export REQUESTS_CA_BUNDLE=/caminho/para/certificados.pem
```

## Erros de Permissão

### Erro: `PermissionError: [Errno 13] Permission denied: 'logs/app.log'`

**Problema**: Falta de permissão para escrever no arquivo de log.

**Solução**:
```bash
# Verificar permissões
ls -la logs/

# Corrigir permissões
chmod -R 755 logs/
chmod 644 logs/*.log
```

## Erros de Memória

### Erro: `MemoryError: ...`

**Problema**: Memória insuficiente para carregar o modelo.

**Solução**:
```bash
# Usar modelo menor
make tdd prompt="Criar API" model=tinyllama-1.1b

# OU ajustar parâmetros de memória
export LLAMA_N_GPU_LAYERS=20  # Carregar apenas parte do modelo na GPU
``` 