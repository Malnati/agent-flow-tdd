# Modo MCP

O Model Context Protocol (MCP) é um protocolo padronizado para comunicação entre componentes que utilizam modelos de linguagem. O Agent Flow TDD implementa este protocolo, permitindo uma integração mais flexível com outras ferramentas e sistemas.

## O que é o MCP?

O MCP (Model Context Protocol) é um protocolo que define um formato padronizado para troca de mensagens entre sistemas que utilizam modelos de linguagem. Ele facilita:

- **Interoperabilidade** entre diferentes ferramentas
- **Padronização** de formatos de mensagem
- **Extensibilidade** através de metadados
- **Rastreabilidade** de contexto

## Inicializando o Servidor MCP

Para iniciar o Agent Flow TDD no modo MCP:

```bash
# Via Makefile
make tdd prompt="" mode=mcp

# Ou diretamente
python -m src.prompt_tdd mcp
```

O servidor MCP será inicializado em background e estará pronto para processar mensagens.

## Formato de Mensagens

### Mensagem de Entrada

As mensagens de entrada para o MCP seguem o formato:

```json
{
  "content": "<texto do prompt>",
  "metadata": {
    "type": "<tipo de operação>",
    "options": {
      "model": "<modelo>",
      "temperature": <temperatura>,
      "format": "<formato>"
    }
  }
}
```

### Campos da Mensagem

| Campo | Descrição | Valores Possíveis | Obrigatório |
|-------|-----------|-------------------|-------------|
| `content` | Texto do prompt | Qualquer texto | Sim |
| `metadata.type` | Tipo de operação | `feature`, `status` | Sim |
| `metadata.options.model` | Modelo a ser usado | Qualquer modelo suportado | Não |
| `metadata.options.temperature` | Temperatura do modelo | 0.0 - 1.0 | Não |
| `metadata.options.format` | Formato de saída | `json`, `markdown`, `text` | Não |

### Mensagem de Saída

As respostas do MCP seguem o formato:

```json
{
  "content": { /* conteúdo da resposta */ },
  "metadata": {
    "status": "<status>",
    "items": <número de itens>,
    "guardrails": <número de guardrails>,
    "raw_responses": <número de respostas>
  }
}
```

## Exemplos de Uso

### Geração de Feature

Enviar:

```json
{
  "content": "Criar sistema de login com autenticação JWT",
  "metadata": {
    "type": "feature",
    "options": {
      "model": "gpt-4-turbo",
      "temperature": 0.7,
      "format": "json"
    }
  }
}
```

Receber:

```json
{
  "content": {
    "name": "Sistema de Login com JWT",
    "description": "Sistema de autenticação utilizando tokens JWT para garantir segurança nas requisições.",
    "acceptance_criteria": [
      "Usuário deve poder se registrar com email e senha",
      "Usuário deve receber um token JWT ao fazer login",
      "Token JWT deve expirar após um tempo determinado",
      "Rotas protegidas devem validar o token JWT"
    ],
    "complexity": 3
  },
  "metadata": {
    "status": "success",
    "items": 4,
    "guardrails": 2,
    "raw_responses": 2
  }
}
```

### Verificação de Status

Enviar:

```json
{
  "content": "",
  "metadata": {
    "type": "status",
    "options": {}
  }
}
```

## Integração com Outras Ferramentas

O MCP facilita a integração do Agent Flow TDD com:

- **Interfaces Web**: Para criar aplicações frontend
- **Sistemas de CI/CD**: Para automação de testes
- **IDEs**: Como plugins para editores de código
- **Outras ferramentas de TDD**: Para complementar funcionalidades

## Comunicação via Arquivos

Por padrão, o Agent Flow TDD usa um sistema de arquivos para a comunicação MCP:

```
logs/mcp_pipe.log    # Arquivo para receber mensagens
logs/mcp_output.log  # Arquivo para enviar respostas
```

### Exemplo de envio de mensagem:

```bash
echo '{
  "content": "Criar API REST",
  "metadata": {
    "type": "feature",
    "options": {
      "model": "tinyllama-1.1b",
      "format": "json"
    }
  }
}' > logs/mcp_pipe.log
```

O servidor MCP processará a mensagem e gravará a resposta em `logs/mcp_output.log`.

## Considerações de Segurança

- O servidor MCP opera apenas localmente por padrão
- Não há autenticação no protocolo base
- Recomenda-se usar o MCP apenas em ambientes confiáveis 