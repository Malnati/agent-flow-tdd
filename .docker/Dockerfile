FROM python:3.11-slim

# Definindo variáveis de ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.7.1

# Instalando dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Criando diretório da aplicação
WORKDIR /app

# Copiando arquivos do projeto
COPY . .

# Instalando dependências Python
RUN pip install --no-cache-dir -e .

# Criando diretórios necessários
RUN mkdir -p logs data

# Porta para possíveis serviços web (opcional)
EXPOSE 8000

# Comando padrão
CMD ["python", "-m", "src.cli"] 