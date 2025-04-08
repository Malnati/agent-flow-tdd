# Agent Flow TDD

<p align="center">
  <img src="assets/flow2.png" alt="Agent Flow TDD Logo" width="400">
</p>

Framework para desenvolvimento orientado a testes usando agentes de IA.

## 🔍 Visão Geral

O Agent Flow TDD utiliza modelos de IA para auxiliar no desenvolvimento orientado a testes, gerando código, testes e documentação com base em prompts.

## 🚀 Início Rápido

```bash
# Clone o repositório
git clone https://github.com/Malnati/agent-flow-tdd.git
cd agent-flow-tdd

# Instale as dependências
make install

# Execute um exemplo
make tdd prompt="Criar API REST em Python" format=json
```

## 📚 Documentação

A documentação completa está disponível no diretório [docs/](docs/):

- **[Visão Geral](docs/overview/README.md)** - Arquitetura e tecnologias
- **[Instalação](docs/installation/README.md)** - Requisitos e configuração
- **[Uso](docs/usage/README.md)** - Comandos e exemplos
- **[Modelos](docs/examples/model-examples.md)** - Exemplos de uso com diferentes modelos
- **[Troubleshooting](docs/troubleshooting/README.md)** - Solução de problemas

## 🔧 Principais Comandos

```bash
# Gerar código/testes a partir de um prompt
make tdd prompt="Criar sistema de login" format=json

# Especificar modelo
make tdd prompt="Implementar ordenação" model=deepseek_local format=python

# Visualizar logs
make logs

# Executar testes
make test
```

## 🤖 Modelos Suportados

### Locais (Offline)
- `tinyllama-1.1b` - TinyLLaMA (1.1B)
- `phi1` - Microsoft Phi-1 (1.3B)
- `deepseek_local` - DeepSeek Coder (6.7B)
- `phi3` - Microsoft Phi-3 Mini

### Remotos (API)
- `gpt-3.5-turbo`, `gpt-4-turbo` - OpenAI
- `claude-3-opus`, `claude-3-sonnet` - Anthropic
- `gemini-pro` - Google

## 📝 Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.