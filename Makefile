# Makefile para o projeto prompt-tdd

.PHONY: help install test run clean autoflake dev db-init db-clean db-backup logs test-e2e publish download-model docs-serve docs-build docs-deploy docs-generate

# Configuração do ambiente virtual
VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip

# URL e nome do modelo TinyLLaMA
MODEL_URL = https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
MODEL_NAME = tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
MODEL_DIR = models

# Carrega variáveis de ambiente do arquivo .env se existir
ifneq (,$(wildcard .env))
    include .env
    export
endif

# Ajuda
help:
	@echo "Comandos disponíveis:"
	@echo ""
	@echo "Ambiente:"
	@echo "  make install      - Instala dependências do projeto"
	@echo "  make clean        - Remove arquivos temporários"
	@echo "  make dev          - Executa em modo desenvolvimento"
	@echo "  make download-model - Baixa o modelo TinyLLaMA"
	@echo ""
	@echo "Documentação:"
	@echo "  make docs-serve   - Inicia servidor local da documentação"
	@echo "  make docs-build   - Gera documentação estática"
	@echo "  make docs-deploy  - Faz deploy da documentação"
	@echo "  make docs-generate - Gera documentação via IA"
	@echo ""
	@echo "Qualidade:"
	@echo "  make test       - Executa testes unitários"
	@echo "  make test-e2e   - Executa testes end-to-end"
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
	@echo "  make dev prompt-tdd=\"Cadastro de pessoas\" mode=mcp format=markdown"
	@echo "  make logs ARGS=\"--limit 20 --session abc123\""

# Instalação e setup
install:
	@echo "🔧 Instalando dependências..."
	python -m venv $(VENV)
	$(PIP) install -e ".[dev,docs]"
	@make download-model || exit 1
	@echo "✅ Instalação concluída!"

# Testes
test:
	@echo "🧪 Executando testes..."
	$(PYTHON) -m pytest src/tests/ -v
	@echo "✅ Testes concluídos!"
	@make autoflake

# Execução do CLI
run:
	@echo "🖥️ Executando CLI..."
	@if [ "$(mode)" = "mcp" ]; then \
		rm -f logs/mcp_pipe.log && \
		echo '{"content": "$(prompt-tdd)", "metadata": {"type": "feature", "options": {"format": "$(format)", "model": "gpt-3.5-turbo", "temperature": 0.7}}}' > logs/mcp_pipe.log && \
		$(PYTHON) -m src.cli "$(prompt-tdd)" --format $(format) --mode $(mode) > logs/mcp_server.log 2>&1 & \
		echo "✅ Servidor MCP iniciado em background (PID: $$!)"; \
	else \
		$(PYTHON) -m src.cli "$(prompt-tdd)" --format $(format) --mode $(mode); \
	fi
	@make autoflake

# Execução do CLI em modo desenvolvimento
dev:
	@echo "🛠️ Executando CLI em modo desenvolvimento..."
	@if [ "$(mode)" = "mcp" ]; then \
		rm -f logs/mcp_pipe.log && \
		echo '{"content": "$(prompt-tdd)", "metadata": {"type": "feature", "options": {"format": "$(format)", "model": "gpt-3.5-turbo", "temperature": 0.7}}}' > logs/mcp_pipe.log && \
		OPENAI_AGENTS_DISABLE_TRACING=0 $(PYTHON) -m src.cli mcp "$(prompt-tdd)" --format $(format) > logs/mcp_server.log 2>&1 & \
		echo "✅ Servidor MCP iniciado em background (PID: $$!)"; \
	else \
		OPENAI_AGENTS_DISABLE_TRACING=0 $(PYTHON) -m src.cli feature "$(prompt-tdd)" --format $(format); \
		RC=$$?; \
		if [ $$RC -ne 0 ]; then \
			exit $$RC; \
		fi \
	fi
	@make autoflake || true

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

# Permite argumentos extras para o comando run
%:
	@:

# Testes end-to-end
test-e2e:
	@echo "🧪 Executando testes end-to-end..."
	@echo "🗄️ Reinicializando banco de dados..."
	@make db-clean
	@make db-init
	$(PYTHON) -m pytest -v -m e2e src/tests/test_e2e.py

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

# Comandos de documentação
docs-serve:
	@echo "🚀 Iniciando servidor de documentação..."
	@$(PYTHON) -m mkdocs serve -f src/configs/mkdocs.yml

docs-build:
	@echo "📚 Gerando documentação estática..."
	@$(PYTHON) -m mkdocs build -f src/configs/mkdocs.yml
	@echo "✅ Documentação gerada em site/"

docs-deploy:
	@echo "🚀 Fazendo deploy da documentação..."
	@$(PYTHON) -m mkdocs gh-deploy --force -f src/configs/mkdocs.yml
	@echo "✅ Documentação publicada!"

docs-generate:
	@echo "🤖 Gerando documentação via IA..."
	@mkdir -p docs
	@echo '{"content": "Gerar documentação", "metadata": {"type": "docs", "options": {"model": "tinyllama-1.1b", "format": "markdown"}}}' > logs/mcp_pipe.log
	@$(PYTHON) src/scripts/generate_docs.py
	@echo "✅ Documentação gerada!" 