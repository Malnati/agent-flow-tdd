# Makefile para o projeto prompt-tdd

.PHONY: help install test run clean autoflake dev db-init db-clean db-backup logs test-e2e publish docs-serve docs-build docs-deploy docs-generate status orchestrator

# Configuração do ambiente virtual
VENV = .venv
PYTHON = python3
PIP = $(PYTHON) -m pip
PYTEST = $(VENV)/bin/pytest

# Define um dir	para cache do Python
export PYTHONPYCACHEPREFIX=cache

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
	@echo ""
	@echo "Documentação:"
	@echo "  make docs-serve   - Inicia servidor local da documentação"
	@echo "  make docs-build   - Gera documentação estática"
	@echo "  make docs-deploy  - Faz deploy da documentação"
	@echo "  make docs-generate - Gera documentação via IA"
	@echo ""
	@echo "Interface de Usuário:"
	@echo "  make orchestrator   - Inicia o orquestrador de agentes TUI"
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
	@echo ""
	@echo "Modelos Disponíveis:"
	@echo "  Modelos Locais:"
	@echo "    - tinyllama-1.1b          - Modelo local TinyLLaMA"
	@echo "    - phi-1                   - Modelo local Phi-1"
	@echo "    - deepseek-coder-6.7b     - Modelo local DeepSeek Coder"
	@echo "    - phi3-mini               - Modelo local Phi-3 Mini"
	@echo "  Modelos Remotos:"
	@echo "    - gpt-3.5-turbo           - OpenAI GPT-3.5 Turbo"
	@echo "    - gpt-4                   - OpenAI GPT-4"
	@echo "    - gemini-pro              - Google Gemini Pro"
	@echo "    - claude-3-opus           - Anthropic Claude 3 Opus"
	@echo ""
	@echo "Exemplo de uso com modelo específico:"
	@echo "  make tdd prompt=\"Cadastro de pessoas\" format=json model=\"deepseek-coder-6.7b\""

# Instalação e setup
install:
	@echo "🔧 Instalando dependências..."
	$(PYTHON) -m venv $(VENV)
	@echo "Ativando ambiente virtual e instalando dependências..."
	@bash -c "source $(VENV)/bin/activate && $(PYTHON) -m pip install --upgrade pip && $(PYTHON) -m pip install -r requirements.txt && $(PYTHON) setup.py develop"
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
	@echo "🔄 Verificando dependências necessárias..."
	@make install
	@$(SHELL) -c "echo $(PWD) && echo '🔄 Incrementando versão...'; PUBLISHING=true ; $(PYTHON) -m src.core.version ;"
	@echo '🚀 Publicando no PyPI...' 
	@$(SHELL) -c "$(PYTHON) -m twine upload dist/* --username __token__ --password $(PYPI_TOKEN) "
	@echo "✅ Pacote publicado com sucesso!"

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

# Orquestrador de agentes TUI
orchestrator:
	@echo "🖥️ Iniciando orquestrador de agentes..."
	@bash -c "source $(VENV)/bin/activate && $(PYTHON) src/ui/agent_orchestrator.py"
	@echo "✅ Orquestrador de agentes finalizado!"

# Permite argumentos extras para o comando run
%:
	@:
