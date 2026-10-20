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
- [[Visao Geral]] — Arquitetura, stack e propósito
- [[Estrutura de Pastas]] — Organização do código-fonte
- [[Tecnologias]] — Stack completa com versões
- [[Padroes de Projeto]] — VSA, DDD, Handler Pattern

### Regras de Negócio
- [[Ciclo de Vida da OS]] — Estados e transições da Ordem de Serviço
- [[Reserva de Estoque]] — Operação atômica e rastreabilidade
- [[Orcamento]] — Geração automática por eventos
- [[Autorizacao e Roles]] — RBAC com Spring Security
- [[Dominio DDD]] — Aggregates, Value Objects, Factory Methods

### Rotas da API
- [[API - Autenticacao]] — Login e Signup
- [[API - Clientes]] — CRUD + Portal do Cliente
- [[API - Veiculos]] — CRUD de veículos
- [[API - Pecas e Suprimentos]] — Partes e insumos
- [[API - Estoque]] — Movimentações e reservas
- [[API - Ordens de Servico]] — Ciclo completo
- [[API - Servicos]] — Serviços dentro da OS
- [[API - Orcamento]] — Consulta de orçamento
- [[API - Monitoramento]] — Analytics de tempo médio

### Como Rodar
- [[Quickstart]] — Subir o projeto em 5 minutos
- [[Requisitos]] — Pré-requisitos e versões
- [[Docker Compose]] — Serviços e orquestração
- [[Rodando Testes]] — Unitários, integração e cobertura

### Ambientes
- [[Variaveis de Ambiente]] — Todas as variáveis configuráveis
- [[Configuracao Local]] — Desenvolvimento local
- [[Configuracao Docker]] — Ambiente containerizado

### Segurança
- [[JWT]] — Geração, validação e claims
- [[OWASP ZAP]] — Scan automático de segurança
- [[Spring Security Config]] — Filtros e regras de acesso

### Qualidade de Código
- [[SonarQube]] — Análise estática e cobertura

### Dados & Teste
- [[Credenciais e Seeds]] — Dados pré-carregados e usuários padrão

---

> [!tip] Início Rápido
> Para subir o projeto agora: [[Quickstart]]
> Para entender o fluxo principal: [[Ciclo de Vida da OS]]
> Para testar a API: [[Credenciais e Seeds]] → [[API - Autenticacao]]
