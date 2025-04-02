# Makefile para o projeto prompt-tdd

.PHONY: install test run clean autoflake

# Configuração do ambiente virtual
VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip

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
		rm -f mcp_pipe && mkfifo mcp_pipe && \
		$(PYTHON) -m src.cli "$(prompt-tdd)" --format $(format) --mode $(mode) > mcp_server.log 2>&1 & \
		echo "✅ Servidor MCP iniciado em background (PID: $$!)" && \
		sleep 2 && \
		echo '{"content": "$(prompt-tdd)", "metadata": {"type": "feature", "options": {"format": "$(format)", "model": "gpt-3.5-turbo", "temperature": 0.7}}}' > mcp_pipe; \
	else \
		$(PYTHON) -m src.cli "$(prompt-tdd)" --format $(format) --mode $(mode); \
	fi
	@make autoflake

# Limpeza de código com autoflake
autoflake:
	@echo "🧹 Limpando código com autoflake..."
	@$(PYTHON) -m autoflake --remove-all-unused-imports --remove-unused-variables --in-place --recursive .
	@echo "✨ Limpeza de código concluída!"

# Limpeza
clean:
	@echo "🧹 Limpando arquivos temporários..."
	@rm -rf .venv *.egg-info dist build .pytest_cache .coverage htmlcov mcp*.log mcp_pipe
	@find . -type d -name __pycache__ -exec rm -rf {} +
	@echo "✨ Limpeza concluída!"

# Permite argumentos extras para o comando run
%:
	@: 