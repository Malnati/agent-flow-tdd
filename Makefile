# Makefile para o projeto prompt-tdd

.PHONY: help install test run clean autoflake dev db-init db-clean db-backup logs test-e2e

# Configuração do ambiente virtual
VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip

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
	@echo "  make install    - Instala dependências do projeto"
	@echo "  make clean      - Remove arquivos temporários"
	@echo "  make dev        - Executa em modo desenvolvimento"
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
	@echo "Exemplos:"
	@echo "  make dev prompt-tdd=\"Cadastro de pessoas\" mode=mcp format=markdown"
	@echo "  make logs ARGS=\"--limit 20 --session abc123\""

# Instalação e setup
install:
	@echo "🔧 Instalando dependências..."
	python -m venv $(VENV)
	$(PIP) install -e ".[dev]"
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
	python src/scripts/utils_view_logs.py $(ARGS)

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