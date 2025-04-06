# Código de Conduta do Projeto

## 📋 Regras Gerais

### 1. Estrutura de Código Python
- Todo código Python deve estar dentro do diretório `src/` ou seus subdiretórios existentes
- Respeitar a estrutura de diretórios:
  - `src/core/` - funcionalidades centrais
  - `src/tests/` - testes
  - `src/configs/` - configurações
  - `src/scripts/` - scripts de utilitários
- É proibido criar novos diretórios na raiz de `src/` sem autorização expressa
- Seguir padrões de nomenclatura:
  - Arquivos: snake_case
  - Classes: PascalCase
  - Funções/métodos: snake_case
  - Constantes: MAIÚSCULAS_COM_UNDERSCORES

### 2. Gestão de Configurações
- Todas as configurações devem estar centralizadas em `src/configs/cli.yaml`
- Não usar arquivos `.env` - configurar variáveis diretamente no ambiente ou via argumentos
- Manter a estrutura hierárquica das configurações:
  - Seção `cli` para configurações do CLI
  - Seção `mcp` para configurações do MCP
  - Seção `app` para configurações da aplicação

### 3. Logging e Monitoramento
- Incluir logs em todas as funções Python seguindo o padrão:
  ```python
  def minha_funcao():
      logger = logging.getLogger(__name__)
      logger.info("INÍCIO - minha_funcao")
      try:
          # Implementação
          logger.debug("Detalhe intermediário")
          return resultado
      except Exception as e:
          logger.error("FALHA - minha_funcao", exc_info=True)
          raise
      finally:
          logger.info("FIM - minha_funcao")
  ```
- Usar níveis apropriados:
  - INFO: entrada/saída de funções
  - DEBUG: valores intermediários
  - ERROR: exceções com stacktrace
- Nunca logar dados sensíveis

### 4. Operações com Arquivos
- Durante refatorações:
  - Verificar diretórios vazios após movimentação de arquivos
  - Remover diretórios vazios automaticamente
  - Remover recursivamente diretórios pais vazios
- Usar a biblioteca Rope para refatorações de código

### 5. Comandos e Automação
- Todo novo comando deve ser:
  - Incluído como target no Makefile
  - Documentado no README.md
  - Seguir o protocolo MDC do projeto
- Padronizar comandos com exemplos de uso
- Manter compatibilidade com comandos existentes

### 6. Testes
- Priorizar modificação dos testes ao invés do código-fonte
- Ao modificar código-fonte:
  - Manter estrutura existente
  - Preservar interfaces públicas
  - Não criar/renomear arquivos sem autorização
  - Não modificar estrutura de diretórios
- Executar testes e2e após qualquer alteração em:
  - Arquivos Python
  - Scripts de automação
  - Configurações
  - Dependências

### 7. Limpeza de Código
- Executar autoflake após alterações em arquivos Python:
  ```bash
  autoflake --remove-all-unused-imports --remove-unused-variables --in-place --recursive .
  ```
- Manter o código limpo e livre de imports não utilizados

### 8. Operações Git
- Não automatizar operações git (commit, pull, push)
- Usuário deve revisar e submeter mudanças manualmente
- Mostrar resumo das alterações para revisão
- Permitir que usuário decida quais arquivos adicionar

### 9. Parâmetros de Modelos
- Não usar valores fixos para parâmetros de modelos
- Permitir configuração via argumentos ou variáveis de ambiente
- Manter flexibilidade para diferentes modelos e configurações

### 10. Nomenclatura de Arquivos
- Não usar termos test/tests exceto para testes reais
- Usar nomes descritivos do papel real do arquivo
- Manter organização e padrões existentes:
  - Estrutura de pacotes
  - Arquivos `__init__.py`
  - Comentários de módulo

## 🤝 Contribuindo

Ao contribuir com este projeto, você concorda em seguir estas regras e manter a qualidade e organização do código. Em caso de dúvidas ou necessidade de exceções, discuta com a equipe antes de fazer alterações.

## 📝 Notas

- Este código de conduta é um documento vivo e pode ser atualizado conforme necessário
- Sugestões de melhorias são bem-vindas através de issues ou pull requests
- Em caso de conflito entre regras, priorize a manutenção da qualidade e organização do código
