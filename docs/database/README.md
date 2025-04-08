# Banco de Dados

O Agent Flow TDD utiliza um banco de dados SQLite para armazenar logs estruturados, histórico de execuções e metadados do sistema.

## Conteúdo

Nesta seção, você encontrará informações sobre:

- [Estrutura](structure.md) - Schema e modelagem de dados
- [Scripts SQL](sql-scripts.md) - Scripts para consultas e manutenção
- [Gerenciador](manager.md) - API do gerenciador de banco de dados
- [Makefile](makefile.md) - Comandos para operações no banco

## Visão Geral

O banco de dados do Agent Flow TDD é projetado para:

1. **Armazenar logs estruturados** de execuções de agentes
2. **Rastrear o histórico** de prompts e respostas
3. **Facilitar diagnósticos** e depuração
4. **Permitir análises** sobre o uso do sistema

## Localização

Por padrão, o banco de dados é armazenado em:

```
logs/agent_logs.db
```

Você pode alterar essa localização usando a variável de ambiente `DB_PATH`.

## Comandos Úteis

### Inicialização do Banco

```bash
make db-init
```

Este comando cria o banco de dados se não existir e garante que todas as tabelas estejam corretamente criadas.

### Limpeza do Banco

```bash
make db-clean
```

Este comando remove o banco de dados existente. Use com cuidado, pois esta operação é irreversível.

### Backup do Banco

```bash
make db-backup
```

Este comando cria uma cópia de segurança do banco de dados atual, armazenando-a com um timestamp em `backups/`.

### Visualização de Logs

```bash
make logs [ARGS="--limit 10"]
```

Este comando permite visualizar os logs armazenados no banco de dados, com opções para filtragem e formatação. 