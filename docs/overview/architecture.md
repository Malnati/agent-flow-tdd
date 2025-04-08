# Arquitetura

O Agent Flow TDD segue uma arquitetura modular e extensível, projetada para facilitar a integração de diferentes modelos de IA e componentes.

## Visão Geral da Arquitetura

A arquitetura do framework é composta por camadas bem definidas, cada uma com responsabilidades específicas:

```
┌─────────────────────────────────────┐
│             Interface               │
│   CLI / MCP / Programmatic API      │
└───────────────┬─────────────────────┘
                │
┌───────────────▼─────────────────────┐
│         Orquestrador (Core)         │
│      AgentOrchestrator / Kernel     │
└───────────────┬─────────────────────┘
                │
    ┌───────────┴───────────┐
    │                       │
┌───▼───────────┐     ┌─────▼─────────┐
│   Guardrails  │     │ Agent Manager │
└───┬───────────┘     └─────┬─────────┘
    │                       │
┌───▼───────────┐     ┌─────▼─────────┐
│ Model Manager │     │  DB Manager   │
└───────────────┘     └───────────────┘
```

## Componentes Principais

### 1. Interface

- **CLI**: Ponto de entrada via linha de comando
- **MCP (Model Context Protocol)**: Interface para comunicação padronizada entre componentes
- **API Programática**: Interface para uso em código Python

### 2. Orquestrador (Core)

- **AgentOrchestrator**: Coordena a execução dos agentes e guardrails
- **Kernel**: Fornece utilitários e configurações globais

### 3. Guardrails

- **InputGuardrail**: Valida e estrutura entradas do usuário
- **OutputGuardrail**: Valida e formata saídas dos modelos

### 4. Agent Manager

- **Gerencia diferentes tipos de agentes**
- **Controla o fluxo de comunicação entre agentes**
- **Aplica transformações de contexto**

### 5. Model Manager

- **Integração com modelos locais e remotos**
- **Gerenciamento de tokens e limites**
- **Cache de respostas e fallback entre modelos**

### 6. DB Manager

- **Armazenamento de logs estruturados**
- **Histórico de execuções**
- **Tracing de operações**

## Fluxo de Dados

1. **Entrada**: O usuário fornece um prompt via CLI, MCP ou API
2. **Validação**: O InputGuardrail valida e estrutura a entrada
3. **Processamento**: O Orquestrador coordena a execução dos agentes
4. **Geração**: O Model Manager envia requisições aos modelos de IA
5. **Validação**: O OutputGuardrail valida e formata a saída
6. **Armazenamento**: O DB Manager registra a execução e seus resultados
7. **Saída**: O resultado é retornado ao usuário no formato solicitado

## Extensibilidade

A arquitetura foi projetada para ser facilmente extensível:

- **Novos Modelos**: Adição simples de novos provedores de IA
- **Novos Guardrails**: Criação de validações customizadas
- **Novos Agentes**: Implementação de agentes especializados
- **Novos Formatos**: Suporte a diferentes formatos de entrada e saída 