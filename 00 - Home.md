---
title: OS Management — Segundo Cérebro
tags:
  - home
  - moc
aliases:
  - Home
  - Index
cssclasses:
  - home-note
---

# OS Management — Segundo Cérebro

> [!abstract] Sobre este Vault
> Documentação técnica completa do sistema **OS Management** — plataforma de gestão digital de ordens de serviço para oficina mecânica. Substitui planilhas e fichas manuais por um sistema centralizado com ciclo de vida completo.

## Mapa de Conteúdo

### Entendendo o Sistema
- [[Visao Geral]] — Os 4 microsserviços, a Saga e a evolução das fases
- [[Decisoes de Arquitetura]] — Por que cada banco, a Saga orquestrada, SNS/SQS, EKS, Lambda…
- [[Evolucao das Fases]] — O que cada fase pediu, onde ficou e se continua na Fase 4
- [[Estrutura de Pastas]] — Repositórios e camadas de cada serviço
- [[Tecnologias]] — Stack completa com versões
- [[Padroes de Projeto]] — Hexagonal, Saga, um caso de uso por classe

### Regras de Negócio
- [[Ciclo de Vida da OS]] — Estados e transições da Ordem de Serviço
- [[Reserva de Estoque]] — Reserva, baixa e liberação (execution)
- [[Orcamento]] — Gerado pela Saga (billing)
- [[Autorizacao e Roles]] — RBAC com Spring Security
- [[Dominio DDD]] — Aggregates, Value Objects, Factory Methods

### Rotas da API
- [[API - Autenticacao]] — Login de cliente e staff (Lambda)
- [[API - Clientes]] — CRUD (customer-service)
- [[API - Veiculos]] — CRUD de veículos
- [[API - Pecas e Suprimentos]] — Peças e insumos (execution-service)
- [[API - Estoque]] — Movimentações e reservas
- [[API - Ordens de Servico]] — Ciclo completo
- [[API - Servicos]] — Catálogo e execução dos serviços da OS
- [[API - Orcamento]] — Orçamento e pagamento (billing-service)
- [[API - Monitoramento]] — Analytics de tempo médio

### Como Rodar
- [[Quickstart]] — Subir a plataforma inteira com um compose
- [[Requisitos]] — Pré-requisitos e versões
- [[Docker Compose]] — Serviços e orquestração
- [[Rodando Testes]] — Unitários, integração e cobertura
- [[Saga Ponta a Ponta]] — Roteiro com curl: fluxo feliz e compensação, sem AWS

### Ambientes
- [[Variaveis de Ambiente]] — Todas as variáveis configuráveis
- [[Configuracao Local]] — Desenvolvimento local
- [[Configuracao Docker]] — Ambiente containerizado

### Segurança
- [[JWT]] — Geração, validação e claims
- [[OWASP ZAP]] — Scan DAST pelo gateway
- [[Relatorio de Vulnerabilidades - Fase 4]] — ZAP + Trivy, achados e correções
- [[Spring Security Config]] — Filtros e regras de acesso

### Qualidade de Código
- [[SonarQube]] — Análise estática e cobertura
- [[Auditoria de Codigo]] — Rodadas de auditoria, achados e decisões

### Operação (AWS)
- [[Deploy na AWS]] — Ligar a stack, fase a fase, com os secrets
- [[Desligar a AWS]] — Destruir tudo para parar a cobrança
- [[Runbook]] — DLQ, OS parada, troca do JWT, rollback

### Dados & Teste
- [[Credenciais e Seeds]] — Dados pré-carregados e usuários padrão

---

> [!tip] Início Rápido
> Para subir o projeto agora: [[Quickstart]]
> Para entender o fluxo principal: [[Ciclo de Vida da OS]]
> Para testar a API: [[Credenciais e Seeds]] → [[API - Autenticacao]]
