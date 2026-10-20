---
title: Estrutura de Pastas
tags:
  - arquitetura
  - estrutura
---

# Estrutura de Pastas

## Raiz do Projeto

```
workbench-monolith/
├── src/
│   ├── main/
│   │   ├── java/com/workbench/workshop/features/   ← código principal
│   │   └── resources/
│   │       └── application.yml              ← configuração Spring
│   └── test/
│       ├── java/                            ← testes unitários e integração
│       └── resources/
│           └── application-integration.yml  ← config do banco de teste
├── zap/
│   ├── zap-scan.sh                          ← script de scan OWASP ZAP
│   └── rules.conf                           ← regras de alerta do ZAP
├── Dockerfile                               ← build multi-stage
├── docker-compose.yml                       ← orquestração dos serviços
├── init.sh                                  ← inicializa schema + dados (588 linhas)
├── validation.sh                            ← testa fluxo completo de OS
└── pom.xml                                  ← dependências Maven
```

## Features (Código Principal)

```
features/
├── WorkshopApplication.java           ← @SpringBootApplication (entry point)
├── DataInitializer.java               ← seed idempotente de dados de teste
│
├── user/                              ← Autenticação e Autorização
│   ├── login/
│   │   ├── LoginHandler.java
│   │   ├── LoginRequest.java
│   │   └── LoginResponse.java
│   ├── signUp/
│   │   ├── SignUpHandler.java
│   │   ├── SignUpRequest.java
│   │   └── SignUpResponse.java
│   └── shared/
│       ├── domain/
│       │   ├── User.java              ← entidade de usuário
│       │   ├── Role.java
│       │   └── Group.java
│       ├── repository/
│       │   ├── UserRepository.java
│       │   └── RoleRepository.java
│       └── security/
│           ├── JwtService.java        ← geração e validação de token
│           ├── JwtFilter.java         ← OncePerRequestFilter
│           ├── JwtProperties.java     ← secret + expiration
│           ├── SecurityConfig.java    ← filter chain + regras de acesso
│           └── CustomUserDetailsService.java
│
├── client/                            ← Gestão de Clientes
│   ├── ClientController.java
│   ├── create/
│   ├── findByCpf/
│   ├── findById/
│   ├── list/
│   ├── update/
│   ├── deactivate/
│   ├── myOrders/                      ← portal do cliente
│   ├── myOrderDetail/
│   ├── approveOrder/
│   └── shared/
│       ├── domain/
│       │   ├── Client.java            ← Aggregate Root com invariantes DDD
│       │   └── Cpf.java               ← Value Object com validação
│       ├── repository/
│       │   ├── ClientEntity.java
│       │   ├── ClientJpaRepository.java
│       │   └── ClientMapper.java      ← MapStruct
│       └── exception/
│
├── vehicle/                           ← Gestão de Veículos
│   ├── VehicleController.java
│   └── shared/domain/ repository/
│
├── product/                           ← Peças e Suprimentos
│   ├── part/
│   │   ├── PartController.java
│   │   └── shared/
│   ├── supply/
│   │   ├── SupplyController.java
│   │   └── shared/
│   ├── domain/                        ← domínio compartilhado de produto
│   └── persistence/
│       ├── ProductEntity.java         ← entidade base (herança)
│       ├── PartEntity.java
│       └── SupplyEntity.java
│
├── stock/                             ← Estoque e Reservas
│   ├── StockController.java
│   ├── create/
│   ├── entry/                         ← entrada de estoque
│   ├── exit/                          ← saída de estoque
│   ├── updateMinimum/
│   ├── reserve/                       ← reserva ATÔMICA multi-produto
│   ├── confirmReservation/
│   ├── releaseReservation/
│   ├── findMovements/
│   ├── findReservations/
│   ├── findByProductId/
│   ├── list/
│   └── shared/
│       ├── domain/
│       │   ├── Stock.java
│       │   ├── StockReservation.java
│       │   └── StockMovement.java
│       └── repository/
│
├── serviceorder/                      ← Ordens de Serviço
│   ├── ServiceOrderController.java
│   ├── create/
│   ├── update/                        ← transições de status
│   ├── findById/
│   ├── list/
│   └── shared/
│       ├── domain/
│       │   ├── ServiceOrder.java
│       │   └── ServiceOrderStatus.java ← enum com 6 estados
│       └── repository/
│
├── service/                           ← Serviços dentro da OS
│   ├── ServiceController.java
│   ├── create/
│   ├── findById/
│   ├── findByServiceOrder/
│   ├── list/
│   ├── listTypes/
│   ├── update/
│   ├── updateStatus/                  ← TO_DO → DOING → DONE
│   └── shared/repository/
│
├── budget/                            ← Orçamento Automático
│   ├── BudgetController.java
│   ├── findByServiceOrder/
│   ├── recalculate/                   ← acionado por ReservationChangedEvent
│   └── shared/
│       ├── domain/
│       │   ├── Budget.java
│       │   └── BudgetItem.java
│       └── repository/
│
├── monitoring/                        ← Analytics
│   ├── MonitoringController.java
│   ├── averageExecutionTime/
│   ├── averageExecutionTimeById/
│   └── shared/domain/
│
└── utils/                             ← utilitários e anotações compartilhadas
```

## Padrão por Feature

Cada feature segue o mesmo padrão interno:

```
featureName/
├── FeatureController.java   ← @RestController, mapeia endpoints
├── useCaseName/
│   ├── UseCaseHandler.java  ← lógica de negócio isolada
│   ├── UseCaseRequest.java  ← DTO de entrada
│   └── UseCaseResponse.java ← DTO de saída
└── shared/
    ├── domain/              ← entidades de domínio
    └── repository/          ← interfaces + JPA adapters
```

## Links Relacionados
- [[Visao Geral]]
- [[Padroes de Projeto]]
