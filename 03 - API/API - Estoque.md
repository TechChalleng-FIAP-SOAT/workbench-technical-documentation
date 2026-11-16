---
title: API — Estoque
tags:
  - api
  - estoque
  - reservas
  - execution
aliases:
  - Stock API
  - Estoque e Reservas
---

# API — Estoque

**Serviço dono:** Execution Service (`/api/stocks`, MongoDB com transação)

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

| Método | Rota | Resposta |
|---|---|---|
| POST | `/api/stocks` | 201 estoque do produto · 404 produto · 409 já existe |
| GET | `/api/stocks` | 200 lista |
| GET | `/api/stocks/low` | 200 abaixo do mínimo |
| GET | `/api/stocks/product/{productId}` | 200 · 404 |
| PATCH | `/api/stocks/product/{productId}/entry` | 200 entrada |
| PATCH | `/api/stocks/product/{productId}/exit` | 200 saída · 409 sem saldo disponível |
| PATCH | `/api/stocks/product/{productId}/minimum` | 200 novo mínimo |
| POST | `/api/stocks/availability` | 200 disponibilidade de uma lista |
| POST | `/api/stocks/reservations` | 201 reserva para uma OS · 409 faltou saldo |
| PATCH | `/api/stocks/reservations/service-order/{id}/confirm` | 200 baixa (orçamento aprovado) |
| PATCH | `/api/stocks/reservations/service-order/{id}/release` | 200 devolve (recusa/compensação) |
| GET | `/api/stocks/reservations/service-order/{id}` | 200 reservas da OS |

Todas: ADMIN, TECHNICIAN.

## POST /api/stocks

```json
{ "productId": "665f...", "quantity": 100, "minimumQuantity": 10 }
```
**201**
```json
{ "id": "...", "productId": "665f...", "quantity": 100, "reservedQuantity": 0,
  "availableQuantity": 100, "minimumQuantity": 10, "lowStock": false }
```

## PATCH .../entry · .../exit

```json
{ "quantity": 5, "reason": "Compra NF 123" }
```
`availableQuantity = quantity − reservedQuantity`; a saída só usa o disponível.

## POST /api/stocks/availability

```json
{ "items": [ { "productId": "665f...", "quantity": 2 } ] }
```
**200** `{ "available": false, "shortages": [ { "productId": "665f...", "requested": 2, "available": 1 } ] }`

## Reservas e a Saga

Normalmente a reserva é feita pela Saga (`ComandoReservarEstoque`), não por REST:

| Evento da OS | Efeito no estoque | Status da reserva |
|---|---|---|
| diagnóstico | reserva (sai do disponível) | `ACTIVE` |
| orçamento aprovado | baixa definitiva | `CONFIRMED` |
| orçamento recusado / compensação | devolve ao disponível | `RELEASED` |

As rotas REST de reserva existem para suporte e testes manuais. Reserva e saldo são
gravados na mesma transação do MongoDB (replica set), e o comando é idempotente por OS.

---

## Links Relacionados
- [[API - Pecas e Suprimentos]]
- [[API - Ordens de Servico]]
