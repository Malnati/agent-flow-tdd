# Interface CLI

A interface de linha de comando (CLI) é a forma mais direta de interagir com o Agent Flow TDD. Ela permite executar todas as funcionalidades do framework através de comandos simples.

## Sintaxe Básica

```bash
make tdd prompt="<texto do prompt>" [format=<formato>] [model=<modelo>] [mode=<modo>] [session_id=<id>]
```

Ou diretamente:

```bash
python -m src.prompt_tdd cli "<texto do prompt>" [--format <formato>] [--model <modelo>] [--session-id <id>]
```

## Parâmetros

| Parâmetro | Descrição | Valores Possíveis | Padrão |
|-----------|-----------|-------------------|--------|
| `prompt` | Texto do prompt a ser processado | Qualquer texto | *(obrigatório)* |
| `format` | Formato de saída | `json`, `markdown`, `text` | `json` |
| `model` | Modelo a ser usado | Qualquer modelo suportado | `tinyllama-1.1b` |
| `mode` | Modo de operação | `cli`, `mcp`, `status` | `cli` |
| `session_id` | ID da sessão | Qualquer string válida | `cli` |

## Exemplos

### Geração de Feature

```bash
# Usando make (recomendado)
make tdd prompt="Criar um sistema de login com autenticação JWT" format=json

# Usando comando direto
python -m src.prompt_tdd cli "Criar um sistema de login com autenticação JWT" --format json
```

### Verificação de Status

```bash
# Usando make
make tdd prompt="" mode=status

# Usando comando direto
python -m src.prompt_tdd cli "" --mode status
```

### Uso de Modelo Específico

```bash
# Modelo local
make tdd prompt="Criar API REST" model=phi-1

# Modelo remoto
make tdd prompt="Criar API REST" model=gpt-4-turbo
```

### Saída em Markdown

```bash
make tdd prompt="Criar sistema de cadastro de usuários" format=markdown
```

## Saída

A saída do comando varia de acordo com o formato especificado:

### JSON

```json
{
  "name": "Sistema de Login com JWT",
  "description": "Sistema de autenticação utilizando tokens JWT para garantir segurança nas requisições.",
  "acceptance_criteria": [
    "Usuário deve poder se registrar com email e senha",
    "Usuário deve receber um token JWT ao fazer login",
    "Token JWT deve expirar após um tempo determinado",
    "Rotas protegidas devem validar o token JWT"
  ],
  "complexity": 3
}
```

### Markdown

```markdown
# Sistema de Login com JWT

## Descrição
Sistema de autenticação utilizando tokens JWT para garantir segurança nas requisições.

## Critérios de Aceite
1. Usuário deve poder se registrar com email e senha
2. Usuário deve receber um token JWT ao fazer login
3. Token JWT deve expirar após um tempo determinado
4. Rotas protegidas devem validar o token JWT

## Complexidade
Média (3/5)
```

## Opções Avançadas

### Configuração de Sessão

```bash
# Usando um ID de sessão específico
make tdd prompt="Criar API REST" session_id=meu-projeto-123
```

### Combinação de Opções

```bash
# Uso avançado com múltiplas opções
make tdd prompt="Criar sistema de notificações" format=markdown model=gpt-4 session_id=notificacoes-app
```

### Variáveis de Ambiente

Você também pode configurar opções através de variáveis de ambiente:

```bash
# Definir variáveis
export DEFAULT_MODEL=gpt-4-turbo
export LOG_LEVEL=DEBUG

# Executar comando
make tdd prompt="Criar API REST"
```

## Mensagens de Erro

As mensagens de erro são formatadas para facilitar a identificação do problema:

```
❌ Erro: Modelo 'modelo-inexistente' não encontrado.
Modelos disponíveis:
- Locais: tinyllama-1.1b, phi-1, deepseek-coder-6.7b, phi3-mini
- Remotos (requerem chave de API): gpt-3.5-turbo, gpt-4, gemini-pro, claude-3-opus
```

## Logs

Os logs da execução são armazenados em:

```
logs/agent_logs.db    # Banco de dados SQLite
logs/app.log          # Logs em formato texto
```

Para visualizar os logs:

```bash
make logs [ARGS="--limit 10"]
``` 