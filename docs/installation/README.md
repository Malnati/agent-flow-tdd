# Instalação

Esta seção contém informações detalhadas sobre como instalar e configurar o Agent Flow TDD.

## Conteúdo

- [Dependências](dependencies.md) - Requisitos e bibliotecas necessárias
- [Ambiente Virtual](virtualenv.md) - Configuração do ambiente virtual Python
- [Variáveis](environment.md) - Configuração de variáveis de ambiente

## Instalação Rápida

Para uma instalação rápida, siga os passos abaixo:

```bash
# Clone o repositório
git clone https://github.com/Malnati/agent-flow-tdd.git
cd agent-flow-tdd

# Instale as dependências
make install
```

O comando `make install` irá:

1. Criar um ambiente virtual Python
2. Instalar todas as dependências necessárias
3. Baixar os modelos locais (TinyLLaMA, Phi-1, DeepSeek, Phi-3)
4. Configurar o banco de dados local

## Verificando a Instalação

Após a instalação, você pode verificar se tudo está funcionando corretamente com:

```bash
make test
```

Este comando irá executar os testes unitários e garantir que todos os componentes estão funcionando conforme esperado.

## Configuração de Modelos

Por padrão, o Agent Flow TDD vem com suporte a modelos locais, que são baixados automaticamente durante a instalação. Para utilizar modelos remotos (como GPT-4 da OpenAI ou Claude da Anthropic), você precisará configurar as respectivas chaves de API.

Consulte a seção [Variáveis](environment.md) para mais informações sobre como configurar as chaves de API. 