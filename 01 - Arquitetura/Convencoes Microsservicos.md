---
title: Convenções de Microsserviços
tags:
  - arquitetura
  - convencoes
  - fase4
---

# Convenções — Microsserviços (Fase 4)

Padrões transversais para os 4 serviços, de modo que repos, filas e observabilidade
sejam consistentes.

## Nomenclatura de repositórios

Um repositório por serviço, prefixo `os-` mantido:

| Serviço | Repositório |
|---|---|
| Customer Service | `os-customer-service` |
| OS Service | `os-service` |
| Billing Service | `os-billing-service` |
| Execution Service | `os-execution-service` |

Repos de infraestrutura existentes permanecem: `workbench-k8s-terraform`,
`workbench-database`, `workbench-lambda`, `workbench-gateway`.

## Estrutura interna (hexagonal, mantida)

```
src/main/java/com/os/<servico>/
├── adapter/in/web        # controllers REST
├── adapter/in/messaging  # consumers SQS
├── adapter/out/persistence
├── adapter/out/messaging # publishers SNS
├── application           # use cases + ports
├── domain                # entidades puras
└── infrastructure        # config, security, observabilidade
```

## Tópicos SNS e filas SQS

- **Tópico por tipo de agregado emissor**, no padrão `os-<dominio>-events`:
  `os-order-events`, `os-billing-events`, `os-execution-events`.
- **Fila por consumidor**, inscrita no(s) tópico(s) que consome:
  `os-<servico>-<proposito>-queue` → ex.: `os-execution-commands-queue`,
  `os-os-saga-replies-queue`.
- **DLQ** sufixada: `<fila>-dlq`, `maxReceiveCount = 3`.
- Provisionadas via Terraform (reaproveitar `workbench-k8s-terraform` ou repo próprio de mensageria).

## Convenções de banco

- Database-per-service: nenhum serviço acessa o schema de outro.
- **Flyway** em todos os serviços SQL (migrations versionadas, substituindo o schema manual atual).
- MongoDB no Execution Service (índices por `serviceOrderId` e `productId`).

## Observabilidade (reaproveita Datadog da Fase 3)

- Logs estruturados JSON (logstash-logback-encoder), já no monólito.
- **Correlação distribuída**: propagar `sagaId` e `correlationId` no MDC e nos headers
  das mensagens, para rastrear uma OS cruzando os 4 serviços.
- Tags Datadog padronizadas: `service:<nome>`, `env:<developer|homolog|production>`.
- Métricas de negócio por serviço (contadores de Saga iniciada/concluída/compensada).

## CI/CD (pipeline independente por serviço)

Cada repo replica o pipeline do monólito, ajustado:
`unit-test → code-analysis (Sonar) → build → docker-build-push → deploy K8s`.

- Cobertura mínima **80%** por serviço (JaCoCo gate).
- Branch `main` protegida: PR obrigatório + checks automáticos.
- Deploy automatizado em Kubernetes (EKS).

## Links Relacionados
- [[Arquitetura Alvo Microsservicos]]
- [[Contratos de Mensagem]]
- [[Visao Geral]]
