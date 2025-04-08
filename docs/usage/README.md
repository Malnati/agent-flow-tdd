# Uso

Esta seção contém informações detalhadas sobre como utilizar o Agent Flow TDD em diferentes cenários e modos de operação.

## Conteúdo

- [Interface CLI](cli.md) - Como usar a interface de linha de comando
- [Modo MCP](mcp.md) - Como usar o protocolo MCP para comunicação
- [Exemplos](examples.md) - Exemplos de uso em diferentes cenários

## Modos de Operação

O Agent Flow TDD pode ser usado de duas formas principais:

### 1. Via Makefile (Recomendado)

```bash
# Criar uma nova feature
make tdd prompt="Criar um sistema de login com autenticação JWT" format=json

# Verificar status do ambiente
make tdd prompt="" mode=status

# Iniciar servidor MCP em background
make tdd prompt="" mode=mcp
```

### 2. Via Comando Direto

Ative o ambiente virtual e use o comando diretamente:

```bash
# Ativar ambiente virtual
source .venv/bin/activate

# Criar uma nova feature
python -m src.prompt_tdd cli "Criar um sistema de login com autenticação JWT" --format json

# Verificar status do ambiente
python -m src.prompt_tdd cli "" --mode status

# Iniciar servidor MCP
python -m src.prompt_tdd mcp
```

## Formatos de Saída

O Agent Flow TDD suporta diferentes formatos de saída:

- **JSON**: Formato estruturado para integração com outras ferramentas
- **Markdown**: Formato legível para documentação e apresentação
- **Text**: Formato de texto simples

## Parâmetros Comuns

Independente do modo de operação, os seguintes parâmetros são comuns:

- **prompt**: O prompt de texto para o modelo
- **format**: O formato de saída (json, markdown)
- **model**: O modelo a ser usado
- **session_id**: ID da sessão para rastreamento

## Integração com Outras Ferramentas

O Agent Flow TDD pode ser facilmente integrado com outras ferramentas de desenvolvimento:

- **Git hooks**: Para validação automática de commits
- **CI/CD**: Para geração de documentação e testes
- **IDEs**: Para uso em scripts de automação

Consulte as subseções para informações mais detalhadas sobre cada modo de operação. 