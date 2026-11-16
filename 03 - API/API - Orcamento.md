---
title: API — Orçamento e Pagamento
tags:
  - api
  - orcamento
  - pagamento
  - billing
  - mercado-pago
aliases:
  - Budget API
  - Payments API
---

# API — Orçamento e Pagamento

**Serviço dono:** Billing Service (`/api/budgets`, `/api/payments`, PostgreSQL)

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

> [!info] Criados pela Saga
> O orçamento nasce do `ComandoGerarOrcamento` (depois da reserva de estoque) e a cobrança
> do `ComandoCobrarPagamento` (OS em `PAGAMENTO_PENDENTE`). As rotas abaixo são de
> consulta — a criação manual existe só para suporte.

| Método | Rota | Perfis | Resposta |
|---|---|---|---|
| GET | `/api/budgets/service-order/{serviceOrderId}` | staff ou o dono da OS | 200 · 403 · 404 |
| GET | `/api/payments/service-order/{serviceOrderId}` | staff ou o dono da OS | 200 última cobrança · 403 · 404 |
| GET | `/api/payments/service-order/{serviceOrderId}/history` | staff ou o dono da OS | 200 histórico |
| POST | `/api/payments/service-order/{serviceOrderId}` | ADMIN, TECHNICIAN | 201 cobrança (manual) |
| POST | `/api/payments/webhook` | **público, só com `PAYMENT_PROVIDER=fake`** | 200 · 404 com o Mercado Pago real |

## GET /api/budgets/service-order/{id}

```json
{ "id": 1, "serviceOrderId": "0c5e...", "totalParts": 90.00, "totalLabor": 80.00, "totalPrice": 170.00,
  "items": [
    { "productId": "665f...", "name": "Óleo 5W30", "sku": "OLEO-5W30", "brand": "Mobil", "itemType": "PART",
      "quantity": 2, "unitPrice": 45.00, "totalPrice": 90.00 },
    { "productId": null, "name": "TROCA_OLEO", "sku": null, "brand": null, "itemType": "LABOR",
      "quantity": 1, "unitPrice": 80.00, "totalPrice": 80.00 } ],
  "createdAt": "...", "updatedAt": "..." }
```

## GET /api/payments/service-order/{id}

```json
{ "id": 3, "serviceOrderId": "0c5e...", "amount": 170.00, "status": "PENDENTE",
  "gatewayPaymentId": "0c5e...-1", "checkoutUrl": "https://www.mercadopago.com.br/checkout/v1/redirect?pref_id=..." }
```
`status`: `PENDENTE`, `PAGAMENTO_APROVADO`, `RECUSADO` ou `ESTORNADO`.

## Como o pagamento é confirmado

- **Mercado Pago (AWS):** Checkout Pro. O `PaymentStatusPollingJob` consulta o Mercado Pago
  a cada `PAYMENT_POLLING_INTERVAL_MS` (30 s) pela referência `<OS>` / `<OS>-N`; ao aprovar,
  publica `PagamentoConfirmado` → OS `PAGO` → `ENTREGUE`. Sem webhook público em produção.
- **Fake (local):** `POST /api/payments/webhook` simula o retorno do gateway:
  ```json
  { "gatewayPaymentId": "0c5e...-1", "approved": true }
  ```
- Recusa → `PagamentoFalhou`; o cliente pode pedir nova cobrança em
  `POST /order/{id}/payment-retry`. O billing implementa o estorno
  (`POST /v1/payments/{id}/refunds` no Mercado Pago) → `ESTORNADO`, mas **nenhum fluxo do os-service
  o dispara hoje** (o comando `ComandoEstornarPagamento` existe no contrato e ainda não é enviado).

---

## Links Relacionados
- [[API - Ordens de Servico]]
- [[API - Estoque]]
