# Testes End-to-End (E2E)

## Visão Geral

Os testes end-to-end (e2e) validam o fluxo completo do Agent Flow TDD, desde a entrada do comando até a geração da saída e armazenamento dos logs.

## Execução

Para executar os testes e2e:

```bash
make test-e2e
```

## Casos de Teste

### 1. Cadastro de Endereços via CLI (Markdown)
- Valida o fluxo completo usando o modo CLI com saída em markdown
- Verifica a execução do comando
- Verifica o registro no banco de dados
- Verifica a formatação da saída

### 2. Cadastro de Endereços via CLI (JSON)
- Valida o fluxo completo usando o modo CLI com saída em JSON
- Verifica a estrutura do JSON de saída
- Verifica o registro no banco de dados

### 3. Tratamento de Erros
- Testa o comportamento quando a chave da API não está disponível
- Verifica mensagens de erro apropriadas

### 4. Integração com Autoflake
- Verifica se o autoflake é executado após a geração
- Valida mensagens de limpeza de código

### 5. Sistema de Logging
- Verifica se os logs são gerados corretamente
- Valida o formato e conteúdo dos logs

## Estrutura dos Testes

Os testes e2e estão organizados em:
- `src/tests/test_e2e.py`: Implementação dos testes
- `pytest.ini`: Configuração do pytest com marcadores
- `Makefile`: Comando para execução dos testes

## Dependências

- Python 3.9+
- pytest
- pytest-cov
- make

## Manutenção

Ao adicionar novos recursos ao Agent Flow TDD:
1. Criar testes e2e correspondentes
2. Atualizar esta documentação
3. Verificar a cobertura de testes 