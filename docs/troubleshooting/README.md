# Troubleshooting

Esta seção contém informações para diagnosticar e resolver problemas comuns que podem ocorrer ao utilizar o Agent Flow TDD.

## Conteúdo

- [Erros Comuns](common-errors.md) - Soluções para problemas frequentes
- [Fallback](fallback.md) - Mecanismo de fallback entre modelos
- [Logs de Execução](execution-logs.md) - Como usar logs para diagnóstico

## Diagnóstico Inicial

Quando encontrar problemas com o Agent Flow TDD, siga estas etapas básicas de diagnóstico:

### 1. Verificar o Status do Sistema

```bash
make status
```

Este comando verifica:
- Versão do Python
- Disponibilidade dos modelos
- Configuração das variáveis de ambiente
- Status do banco de dados

### 2. Verificar os Logs

```bash
# Visualizar logs recentes
make logs

# Visualizar logs de erro
tail -f logs/error.log
```

### 3. Verificar o Ambiente

```bash
# Listar variáveis de ambiente
env | grep OPENAI
env | grep MODEL
env | grep LOG

# Verificar a instalação
pip list | grep agent-flow
```

## Problemas Comuns

### Falha ao Inicializar Modelos Locais

Se encontrar erros relacionados aos modelos locais:

```bash
# Verificar se os modelos foram baixados
ls -la models/

# Re-baixar os modelos
make download-model
make download-phi1
make download-deepseek
make download-phi3
```

### Falha em Requisições a Modelos Remotos

Se os modelos remotos não estiverem respondendo:

```bash
# Verificar a configuração da chave de API
echo $OPENAI_API_KEY

# Testar a conexão
curl -s -X GET https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" | head -20
```

### Banco de Dados Corrompido

Se encontrar erros relacionados ao banco de dados:

```bash
# Verificar a integridade do banco
echo "PRAGMA integrity_check;" | sqlite3 logs/agent_logs.db

# Reinicializar o banco (cuidado: perda de dados)
make db-clean
make db-init
```

## Ferramentas de Diagnóstico

### Modo Verbose

Para obter mais informações durante a execução:

```bash
# Ativar modo verbose com nível DEBUG
LOG_LEVEL=DEBUG make tdd prompt="Criar API REST"
```

### Teste de Conectividade

Para testar a conectividade com APIs externas:

```bash
# OpenAI
curl -s -X GET https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" | head -20

# Anthropic
curl -s -X GET https://api.anthropic.com/v1/models \
  -H "x-api-key: $ANTHROPIC_KEY" | head -20
```

### Limpeza de Cache

Para resolver problemas relacionados ao cache:

```bash
# Limpar o cache
rm -rf cache/*

# Ou via comando
make clean-cache
```

## Obter Ajuda

Se você não conseguir resolver o problema, procure ajuda:

1. **Consulte a Documentação**: Verifique as seções relevantes da documentação
2. **Verifique os Issues**: No repositório do GitHub
3. **Abra um Novo Issue**: Forneça informações detalhadas sobre o problema
   - Passos para reproduzir
   - Logs relevantes
   - Configuração do sistema
   - Variáveis de ambiente (omitindo valores sensíveis) 