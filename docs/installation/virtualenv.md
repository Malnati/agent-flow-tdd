# Ambiente Virtual

O Agent Flow TDD utiliza ambientes virtuais Python para isolar suas dependências e garantir uma execução consistente.

## O que é um Ambiente Virtual?

Um ambiente virtual Python é um ambiente isolado onde você pode instalar pacotes sem afetar o sistema global ou outros projetos. Isso é especialmente útil para projetos como o Agent Flow TDD, que possuem dependências específicas.

## Criação do Ambiente Virtual

O processo de instalação do Agent Flow TDD cria automaticamente um ambiente virtual chamado `.venv` no diretório do projeto. No entanto, você também pode criar manualmente o ambiente virtual.

### Criação Automática (Via Make)

```bash
make install
```

Este comando criará o ambiente virtual `.venv` e instalará todas as dependências necessárias.

### Criação Manual

```bash
# Linux/macOS
python3 -m venv .venv

# Windows
python -m venv .venv
```

## Ativação do Ambiente Virtual

Antes de executar qualquer comando do Agent Flow TDD, você precisa ativar o ambiente virtual.

### Linux/macOS

```bash
source .venv/bin/activate
```

### Windows

```bash
.venv\Scripts\activate
```

## Verificação

Após ativar o ambiente virtual, você verá que o prompt do terminal é prefixado com `(.venv)`, indicando que o ambiente está ativo.

Para verificar a instalação, você pode executar:

```bash
python -c "import src.core; print('Environment OK')"
```

## Desativação

Quando terminar de usar o Agent Flow TDD, você pode desativar o ambiente virtual:

```bash
deactivate
```

## Uso com Makefile

O Makefile do projeto já inclui a ativação automática do ambiente virtual para todos os comandos, então não é necessário ativar manualmente se você estiver usando o make:

```bash
# Isso já ativa o ambiente virtual internamente
make tdd prompt="Criar API REST"
```

## Recriação do Ambiente

Se você encontrar problemas com o ambiente virtual, pode recriá-lo:

```bash
# Remove o ambiente atual
rm -rf .venv

# Cria um novo ambiente
make install
```

## Ambientes Virtuais Alternativos

O Agent Flow TDD suporta outros métodos de gerenciamento de ambientes virtuais, como:

### Conda

```bash
# Criar ambiente
conda create -n agent-flow python=3.13
conda activate agent-flow

# Instalar
pip install -e .
```

### pipenv

```bash
# Instalar pipenv
pip install pipenv

# Instalar com pipenv
pipenv install -e .

# Ativar
pipenv shell
``` 