---
title: API — Monitoramento
tags:
  - api
  - monitoramento
  - metricas
aliases:
  - Monitoring API
---

# API — Monitoramento

**Serviço dono:** OS Service (`/monitoring`)

> [!info] Onde chamar
> - **AWS:** sempre pelo API Gateway — `{{gatewayUrl}}{path}`. O gateway roteia
>   `/api/clients|vehicles|users` → Customer, `/api/budgets|payments` → Billing,
>   `/api/products|stocks` → Execution e o resto (`/order`, `/service-types`,
>   `/monitoring`) → OS Service.
> - **Local:** `docker compose -f workbench-messaging/docker-compose.dev.yml --profile app up -d --build`
>   e use o gateway local `http://localhost:8000` (mesmo roteamento) ou o serviço direto:
>   OS `:8080`, Customer `:8081`, Billing `:8082`, Execution `:8083`.
> - Todas as rotas abaixo exigem `Authorization: Bearer <jwt>` salvo indicação contrária.
>   Erros seguem `{"timestamp": "...", "status": 409, "error": "mensagem em português"}`.

Tempo de execução dos serviços, medido do primeiro `DOING` ao primeiro `DONE` de cada
serviço da OS (ver [[API - Servicos]]). Serviço que ainda não terminou não entra na média.

| Método | Rota | Perfis | Resposta |
|---|---|---|---|
| POST | `/monitoring/all` | ADMIN, TECHNICIAN | 200 média por tipo de serviço |
| POST | `/monitoring/by-id` | ADMIN, TECHNICIAN | 200 tempo de um serviço · 404 |

## POST /monitoring/all

```json
{ "timeUnit": "MINUTES" }
```
`timeUnit`: `SECONDS`, `MINUTES` ou `HOURS`.

**200**
```json
[ { "serviceTypeName": "TROCA_OLEO", "averageTime": 42.5 },
  { "serviceTypeName": "ALINHAMENTO", "averageTime": 30.0 } ]
```

## POST /monitoring/by-id

```json
{ "id": "e2a4...", "timeUnit": "MINUTES" }
```
`id` é o **serviço da OS** (o `id` de `GET /order/{id}/services`).

**200** `{ "serviceTypeName": "TROCA_OLEO", "averageTime": 41.0 }`

> [!tip] Observabilidade
> Além deste relatório, cada serviço publica métricas no Datadog (tempo em cada status
> da OS, falhas por operação, passos da Saga) — dashboards em `datadog/` de cada repo.

---

## Links Relacionados
- [[API - Servicos]]
- [[API - Ordens de Servico]]
