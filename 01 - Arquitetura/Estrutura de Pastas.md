---
title: Estrutura de Pastas
tags:
  - arquitetura
  - estrutura
aliases:
  - Pastas
  - Repositórios
---

# Estrutura de Pastas

## Repositórios

| Repositório | Conteúdo |
|---|---|
| `workbench-os-service` | OS, catálogo de serviços, monitoramento, **orquestrador da Saga** |
| `workbench-customer-service` | Clientes, veículos, usuários staff |
| `workbench-billing-service` | Orçamento e pagamento |
| `workbench-execution-service` | Produtos, estoque e reservas |
| `workbench-messaging` | Terraform SNS/SQS/DLQ, contrato da Saga, **docker-compose** local, ZAP |
| `workbench-gateway` | API Gateway (Terraform) |
| `workbench-lambda` | Lambdas de login e authorizer |
| `workbench-k8s-terraform` | Cluster EKS e rede |
| `workbench-database` | RDS (um por serviço) |
| `workbench-technical-documentation` | Esta documentação + Postman |
| `workbench-monolith` | Monólito das fases 1–3 (histórico) e ADRs |

## Dentro de um microsserviço

```
src/main/java/com/workbench/workshop/
├── domain/<contexto>/          agregados, enums, value objects, exceções
├── application/<contexto>/     *UseCase (um por classe) + port/out/
├── adapter/
│   ├── in/web/<recurso>/       *Controller + DTOs (records)
│   └── out/persistence/        *PersistenceAdapter (implementa as portas)
└── infrastructure/
    ├── config/                 GlobalExceptionHandler, beans
    ├── security/               SecurityConfig, JwtFilter, JsonSecurityErrorHandler
    ├── messaging/              publishers/consumers SNS/SQS
    ├── persistence/            entidades JPA/Mongo + Spring Data
    └── scheduling/             jobs (ShedLock)
src/main/resources/
├── application.yml             tudo configurável por variável de ambiente
├── logback-spring.xml          logs JSON
└── db/migration/               Flyway (Postgres)
src/test/java/...               unit, controller, integration (Testcontainers), contract, bdd
k8s/                            Deployment, Service, HPA, ConfigMap, Secret
datadog/                        dashboards e monitores
.github/workflows/pipeline.yml  CI/CD
```

## Links Relacionados
- [[Padroes de Projeto]]
- [[Visao Geral]]
