# Makefile para o projeto prompt-tdd

.PHONY: help install test run clean autoflake dev db-init db-clean db-backup logs test-e2e publish download-model docs-serve docs-build docs-deploy docs-generate status

# Configuração do ambiente virtual
VENV = .venv
PYTHON = python3
PIP = $(PYTHON) -m pip
PYTEST = $(VENV)/bin/pytest

# URL e nome do modelo TinyLLaMA
MODEL_URL = https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
MODEL_NAME = tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
MODEL_DIR = models

# Carrega variáveis de ambiente do arquivo .env se existir
ifneq (,$(wildcard .env))
    include .env
    export
endif

# Definição de variáveis com valores padrão
prompt ?= Olá
format ?= json
session_id ?= cli
mode ?= cli
model ?=

# Ajuda
help:
	@echo "Comandos disponíveis:"
	@echo ""
	@echo "Ambiente:"
	@echo "  make install      - Instala dependências do projeto"
	@echo "  make clean        - Remove arquivos temporários"
	@echo "  make download-model - Baixa o modelo TinyLLaMA"
	@echo "  make download-phi1  - Baixa o modelo Phi-1"
	@echo ""
	@echo "Documentação:"
	@echo "  make docs-serve   - Inicia servidor local da documentação"
	@echo "  make docs-build   - Gera documentação estática"
	@echo "  make docs-deploy  - Faz deploy da documentação"
	@echo "  make docs-generate - Gera documentação via IA"
	@echo ""
	@echo "Qualidade:"
	@echo "  make test       - Executa todos os testes"
	@echo "  make coverage   - Gera relatório de cobertura"
	@echo "  make lint       - Executa linters"
	@echo "  make format     - Formata código"
	@echo ""
	@echo "Banco de Dados:"
	@echo "  make db-init    - Inicializa banco de dados"
	@echo "  make db-clean   - Remove banco de dados"
	@echo "  make db-backup  - Faz backup do banco"
	@echo "  make logs       - Visualiza logs do banco"
	@echo ""
	@echo "Publicação:"
	@echo "  make publish    - Publica pacote no PyPI"
	@echo ""
	@echo "Exemplos:"
	@echo "  make tdd prompt=\"Cadastro de pessoas\" format=json"
	@echo "  make logs ARGS=\"--limit 20 --session abc123\""

# Instalação e setup
install:
	@echo "🔧 Instalando dependências..."
	$(PYTHON) -m venv $(VENV)
	@echo "Ativando ambiente virtual e instalando dependências..."
	@bash -c "source $(VENV)/bin/activate && $(PYTHON) -m pip install --upgrade pip && $(PYTHON) -m pip install -e \".[dev,docs]\""
	@make download-model || exit 1
	@make download-phi1 || exit 1
	@make download-deepseek || exit 1
	@make download-phi3 || exit 1
	@echo "✅ Instalação concluída!"

# Testes
test:
	@echo "🧪 Executando testes..."
	$(PYTHON) -m pytest src/tests/test.py -v
	@echo "✅ Testes concluídos!"
	@make autoflake

# Execução do CLI
tdd:
	@echo "🖥️ Executando CLI..."
	@bash -c "source $(VENV)/bin/activate && \
		if [ \"$(mode)\" = \"mcp\" ]; then \
			rm -f logs/mcp_pipe.log && \
			echo '{\"content\": \"$(prompt)\", \"metadata\": {\"type\": \"feature\", \"options\": {\"format\": \"$(format)\", \"model\": \"$(model)\", \"temperature\": 0.7}}}' > logs/mcp_pipe.log && \
			$(PYTHON) -m src.prompt_tdd mcp > logs/mcp_server.log 2>&1 & \
			echo \"✅ Servidor MCP iniciado em background (PID: $$!)\"; \
		else \
			$(PYTHON) -m src.prompt_tdd cli \"$(prompt)\" --format $(format) --session-id $(session_id) $${model:+--model $(model)}; \
		fi"

# Limpeza de código com autoflake
autoflake:
	@echo "🧹 Limpando código com autoflake..."
	@find . -type f -name "*.py" -not -path "./.venv/*" -exec autoflake --remove-all-unused-imports --remove-unused-variables --in-place {} \;
	@echo "✨ Limpeza de código concluída!"

# Limpeza geral
clean:
	@echo "🧹 Limpando arquivos temporários..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type f -name "coverage.xml" -delete
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	@echo "✨ Limpeza concluída!"

# Comandos de banco de dados
db-init:
	@echo "🗄️ Inicializando banco de dados..."
	@mkdir -p logs
	@$(PYTHON) -c "from src.core.db import DatabaseManager; DatabaseManager()"
	@echo "✅ Banco de dados inicializado!"

db-clean:
	@echo "🧹 Limpando banco de dados..."
	@rm -f logs/agent_logs.db
	@echo "✅ Banco de dados removido!"

db-backup:
	@echo "💾 Criando backup do banco de dados..."
	@mkdir -p backups
	@if [ -f logs/agent_logs.db ]; then \
		cp logs/agent_logs.db backups/agent_logs_$$(date +%Y%m%d_%H%M%S).db; \
		echo "✅ Backup criado em backups/agent_logs_$$(date +%Y%m%d_%H%M%S).db"; \
	else \
		echo "❌ Banco de dados não encontrado!"; \
	fi

# Visualização de logs
logs:
	$(PYTHON) src/scripts/utils_view_logs.py $(ARGS)

# Publicação no PyPI
publish:
	@echo "📦 Preparando pacote para publicação..."
	@if [ -z "$(PYPI_TOKEN)" ]; then \
		echo "❌ Erro: Variável PYPI_TOKEN não definida"; \
		exit 1; \
	fi
	@echo "🔄 Incrementando versão..."
	@PUBLISHING=true $(PYTHON) -c "from src.core.kernel import VersionAnalyzer; v = VersionAnalyzer(); v.smart_bump()"
	@make clean
	@echo "📥 Instalando dependências de build..."
	@$(PIP) install --upgrade pip build twine
	@echo "🔨 Construindo distribuição..."
	@$(PYTHON) -m build
	@echo "🚀 Publicando no PyPI..."
	@PUBLISHING=true $(PYTHON) -m twine upload dist/* --username __token__ --password $(PYPI_TOKEN)
	@echo "✅ Pacote publicado com sucesso!"

# Download do modelo TinyLLaMA
download-model:
	@echo "📥 Baixando modelo TinyLLaMA..."
	@mkdir -p $(MODEL_DIR)
	@if [ -f "$(MODEL_DIR)/$(MODEL_NAME)" ]; then \
		echo "✅ Modelo já existe em $(MODEL_DIR)/$(MODEL_NAME)"; \
	else \
		echo "🔄 Iniciando download..."; \
		if ! curl -L -f $(MODEL_URL) -o $(MODEL_DIR)/$(MODEL_NAME); then \
			echo "❌ Falha no download do modelo"; \
			rm -f $(MODEL_DIR)/$(MODEL_NAME); \
			exit 1; \
		fi; \
		echo "✅ Download concluído em $(MODEL_DIR)/$(MODEL_NAME)"; \
	fi

# Download do modelo Phi-1
download-phi1:
	@echo "📥 Baixando modelo Phi-1..."
	@mkdir -p $(MODEL_DIR)
	@if [ -f "$(MODEL_DIR)/phi-1.Q4_K_M.gguf" ]; then \
		echo "✅ Modelo já existe em $(MODEL_DIR)/phi-1.Q4_K_M.gguf"; \
	else \
		echo "🔄 Iniciando download..."; \
		if ! curl -L -f https://huggingface.co/professorf/phi-1-gguf/resolve/main/phi-1-f16.gguf -o $(MODEL_DIR)/phi-1.Q4_K_M.gguf; then \
			echo "❌ Falha no download do modelo"; \
			rm -f $(MODEL_DIR)/phi-1.Q4_K_M.gguf; \
			exit 1; \
		fi; \
		echo "✅ Download concluído em $(MODEL_DIR)/phi-1.Q4_K_M.gguf"; \
	fi

# Download do modelo DeepSeek Coder
download-deepseek:
	@echo "📥 Baixando modelo DeepSeek Coder..."
	@mkdir -p $(MODEL_DIR)
	@if [ -f "$(MODEL_DIR)/deepseek-coder-6.7b.Q4_K_M.gguf" ]; then \
		echo "✅ Modelo já existe em $(MODEL_DIR)/deepseek-coder-6.7b.Q4_K_M.gguf"; \
	else \
		echo "🔄 Iniciando download..."; \
		if ! curl -L -f https://huggingface.co/TheBloke/deepseek-coder-6.7B-instruct-GGUF/resolve/main/deepseek-coder-6.7b-instruct.Q4_K_M.gguf -o $(MODEL_DIR)/deepseek-coder-6.7b.Q4_K_M.gguf; then \
			echo "❌ Falha no download do modelo"; \
			rm -f $(MODEL_DIR)/deepseek-coder-6.7b.Q4_K_M.gguf; \
			exit 1; \
		fi; \
		echo "✅ Download concluído em $(MODEL_DIR)/deepseek-coder-6.7b.Q4_K_M.gguf"; \
	fi

# Download do modelo Phi-3 Mini
download-phi3:
	@echo "📥 Baixando modelo Phi-3 Mini..."
	@mkdir -p $(MODEL_DIR)
	@if [ -f "$(MODEL_DIR)/phi-3-mini-4k-instruct.gguf" ]; then \
		echo "✅ Modelo já existe em $(MODEL_DIR)/phi-3-mini-4k-instruct.gguf"; \
	else \
		echo "🔄 Instalando huggingface-cli se necessário..."; \
		pip install -q huggingface-hub; \
		echo "🔄 Iniciando download do modelo Phi-3..."; \
		huggingface-cli download microsoft/Phi-3-mini-4k-instruct-gguf Phi-3-mini-4k-instruct-q4.gguf --local-dir $(MODEL_DIR) --local-dir-use-symlinks False; \
		if [ -f "$(MODEL_DIR)/Phi-3-mini-4k-instruct-q4.gguf" ]; then \
			mv $(MODEL_DIR)/Phi-3-mini-4k-instruct-q4.gguf $(MODEL_DIR)/phi-3-mini-4k-instruct.gguf; \
			echo "✅ Download concluído e renomeado em $(MODEL_DIR)/phi-3-mini-4k-instruct.gguf"; \
		else \
			echo "❌ Falha no download do modelo"; \
			exit 1; \
		fi; \
	fi

# Comandos de documentação
docs-serve:
	@echo "🚀 Iniciando servidor de documentação..."
	@$(PYTHON) -m mkdocs serve

docs-build:
	@echo "🏗️ Gerando documentação estática..."
	@$(PYTHON) -m mkdocs build

docs-deploy:
	@echo "🚀 Publicando documentação..."
	@$(PYTHON) -m mkdocs gh-deploy

docs-generate:
	@echo "🤖 Gerando documentação via IA..."
	@$(PYTHON) src/scripts/generate_docs.py

# Permite argumentos extras para o comando run
%:
	@:
