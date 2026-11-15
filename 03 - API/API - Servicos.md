---
title: API — Serviços
tags:
  - api
  - servicos
  - catalogo
  - execucao
aliases:
  - Services API
  - Service Types API
---

# API — Serviços

**Serviço dono:** OS Service (`/service-types` e `/order/{id}/services`)

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

> [!info] Tipo de serviço × serviço da OS
> - **Tipo de serviço** é o catálogo (ex.: `TROCA_OLEO`), com custo e horas de mão de obra padrão.
> - **Serviço da OS** é a instância daquele tipo dentro de uma OS, com status próprio
>   `TO_DO → DOING → DONE`. Quando o último serviço fica `DONE`, a OS vai para `FINALIZADA`.

## Catálogo — `/service-types` · ADMIN, TECHNICIAN

| Método | Rota | Resposta |
|---|---|---|
| GET | `/service-types` | 200 lista |
| GET | `/service-types/{id}` | 200 · 404 |
| POST | `/service-types` | 201 · 409 nome já existe · 400 dados inválidos |
| PUT | `/service-types/{id}` | 200 (descrição + mão de obra) · 404 |
| PUT | `/service-types/{id}/labor-cost` | 200 (só mão de obra) · 404 |
| DELETE | `/service-types/{id}` | 204 · 404 |

### POST /service-types

```json
{ "name": "troca de pastilha", "description": "Troca das pastilhas dianteiras", "laborCost": 120.00, "laborHours": 1.5 }
```
**201**
```json
{ "id": "7b1c...", "name": "TROCA_DE_PASTILHA", "description": "Troca das pastilhas dianteiras",
  "laborCost": 120.00, "laborHours": 1.5 }
```
- O nome é normalizado (maiúsculas, espaços → `_`) e **não muda depois**: é a chave que a
  OS e o diagnóstico usam.
- `laborCost` e `laborHours` ≥ 0 (padrão de custo: 0).

### PUT /service-types/{id}

```json
{ "description": "Troca de pastilhas (eixo dianteiro)", "laborCost": 130.00, "laborHours": 1.5 }
```
`laborCost` obrigatório. `PUT /{id}/labor-cost` aceita só `{ "laborCost": ..., "laborHours": ... }`.

> [!note] Excluir um tipo
> As OS já abertas guardam o **nome** do tipo, então seguem funcionando; o tipo excluído
> só deixa de poder ser usado em OS novas (422 na abertura).

## Execução — serviços de uma OS · ADMIN, TECHNICIAN

### GET /order/{id}/services

**200**
```json
[ { "id": "e2a4...", "serviceType": "TROCA_OLEO", "laborCost": 80.00, "laborHours": 1.0,
    "status": "DOING",
    "history": [ { "status": "TO_DO", "changedAt": "..." }, { "status": "DOING", "changedAt": "..." } ] } ]
```

### PATCH /order/{id}/services/{serviceId}/status

```json
{ "status": "DOING" }
```
| Status | Quando |
|---|---|
| 200 | serviço avançou (corpo = serviço atualizado) |
| 400 | `status` ausente |
| 404 | OS inexistente ou serviço não pertence à OS |
| 409 | OS fora de `EM_EXECUCAO` |
| 422 | pulou etapa ou voltou (só `TO_DO → DOING → DONE`) |

O histórico (`DOING` → `DONE`) alimenta o tempo médio de execução — [[API - Monitoramento]].

---

## Links Relacionados
- [[API - Ordens de Servico]]
- [[API - Monitoramento]]
- [[Ciclo de Vida da OS]]
