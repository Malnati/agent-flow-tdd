# Exemplos

Esta seção contém exemplos práticos de uso do Agent Flow TDD em diferentes cenários.

## Exemplo 1: Criar uma API REST

### Via CLI

```bash
make tdd prompt="Criar uma API REST para um sistema de e-commerce, com endpoints para produtos, categorias, usuários e pedidos. Incluir autenticação JWT e documentação Swagger." format=json
```

### Saída

```json
{
  "name": "API REST para E-commerce",
  "description": "API REST completa para um sistema de e-commerce com gerenciamento de produtos, categorias, usuários e pedidos, incluindo autenticação JWT e documentação Swagger.",
  "acceptance_criteria": [
    "A API deve ter endpoints para CRUD de produtos",
    "A API deve ter endpoints para CRUD de categorias",
    "A API deve ter endpoints para registro e autenticação de usuários",
    "A API deve ter endpoints para gerenciamento de pedidos",
    "Todas as rotas protegidas devem validar tokens JWT",
    "A API deve ter documentação Swagger acessível via endpoint /api/docs",
    "Os dados devem ser validados antes de serem processados",
    "Erros devem retornar mensagens claras e códigos HTTP apropriados"
  ],
  "complexity": 4,
  "test_scenarios": [
    "Dado um produto válido, quando enviado para o endpoint de criação, então deve retornar status 201 e o produto criado",
    "Dado um usuário válido, quando registrado, então deve poder fazer login e receber um token JWT",
    "Dado um token inválido, quando acessar uma rota protegida, então deve receber status 401",
    "Dado um pedido completo, quando enviado para o endpoint de pedidos, então deve criar o pedido e retornar os detalhes"
  ]
}
```

## Exemplo 2: Sistema de Autenticação com Markdown

### Via CLI

```bash
make tdd prompt="Criar um sistema de autenticação com login, registro, recuperação de senha e autenticação de dois fatores" format=markdown
```

### Saída

```markdown
# Sistema de Autenticação Completo

## Descrição
Sistema completo de autenticação incluindo funcionalidades de login, registro de usuários, recuperação de senha e autenticação de dois fatores (2FA).

## Critérios de Aceite

1. **Registro de Usuários**
   - Usuários devem poder se registrar com nome, email e senha
   - Sistema deve validar formato de email e força da senha
   - Sistema deve enviar email de confirmação de conta

2. **Login**
   - Usuários devem poder fazer login com email e senha
   - Sistema deve bloquear conta após múltiplas tentativas falhas
   - Sistema deve registrar data e IP de acesso

3. **Recuperação de Senha**
   - Usuários devem poder solicitar recuperação via email
   - Links de recuperação devem expirar após 24 horas
   - Sistema deve permitir criação de nova senha

4. **Autenticação de Dois Fatores (2FA)**
   - Usuários devem poder habilitar 2FA via app ou SMS
   - Sistema deve gerar códigos temporários
   - Sistema deve fornecer códigos de backup

## Complexidade
Alta (4/5)

## Cenários de Teste

### Registro
Dado um email válido e senha forte, quando o usuário se registra, então deve receber email de confirmação e conta deve ser criada.

### Login
Dado um usuário registrado, quando inserir credenciais corretas, então deve ser autenticado e receber token de acesso.

### Recuperação
Dado um usuário com conta ativa, quando solicitar recuperação de senha, então deve receber email com link seguro para redefinição.

### 2FA
Dado um usuário com 2FA ativado, quando fizer login com senha correta, então deve ser solicitado código adicional antes de completar autenticação.
```

## Exemplo 3: Uso de Diferentes Modelos

### Modelo Local (TinyLLaMA)

```bash
make tdd prompt="Criar um serviço de notificações por email" model=tinyllama-1.1b
```

### Modelo Local (Phi-3)

```bash
make tdd prompt="Criar um serviço de notificações por email" model=phi3-mini
```

### Modelo Remoto (GPT-4)

```bash
# Configurar chave de API
export OPENAI_API_KEY="sua-chave-aqui"

# Executar com GPT-4
make tdd prompt="Criar um serviço de notificações por email" model=gpt-4-turbo
```

## Exemplo 4: Uso via MCP

### Iniciar Servidor MCP

```bash
make tdd prompt="" mode=mcp
```

### Enviar Requisição

```bash
echo '{
  "content": "Criar um cadastro de produtos com validação",
  "metadata": {
    "type": "feature",
    "options": {
      "model": "tinyllama-1.1b",
      "format": "json"
    }
  }
}' > logs/mcp_pipe.log
```

### Ler Resposta

```bash
cat logs/mcp_output.log
```

## Exemplo 5: Integração com Scripts

```python
#!/usr/bin/env python3
import json
import subprocess
import sys

def generate_feature(prompt, model="tinyllama-1.1b", format="json"):
    """Gera uma feature usando o Agent Flow TDD."""
    cmd = [
        "make", "tdd", 
        f"prompt={prompt}", 
        f"model={model}", 
        f"format={format}"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Erro: {result.stderr}")
        sys.exit(1)
        
    output = result.stdout
    
    # Extrair o JSON da saída
    if format == "json":
        start_idx = output.find('{')
        if start_idx != -1:
            json_str = output[start_idx:]
            return json.loads(json_str)
    
    return output

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: ./gerar_feature.py 'Descrição da feature'")
        sys.exit(1)
        
    prompt = sys.argv[1]
    result = generate_feature(prompt)
    
    print(f"Feature: {result['name']}")
    print(f"Complexidade: {result['complexity']}/5")
    print("\nCritérios de Aceite:")
    for i, criteria in enumerate(result['acceptance_criteria'], 1):
        print(f"{i}. {criteria}")
```

## Exemplo 6: Integração com Git Hooks

Crie um arquivo `.git/hooks/pre-commit`:

```bash
#!/bin/bash

# Verifica se há alterações não commitadas
if git diff --cached --name-only | grep -q "\.py$"; then
    echo "🔍 Verificando código Python..."
    
    # Executa autoflake para remover imports não utilizados
    make autoflake
    
    # Se houver alterações após o autoflake, adiciona-as ao commit
    if ! git diff-index --quiet HEAD --; then
        echo "🧹 Imports não utilizados foram removidos e adicionados ao commit"
        git add $(git diff --name-only | grep "\.py$")
    fi
fi

exit 0
``` 