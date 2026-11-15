---
title: API — Peças e Insumos
tags:
  - api
  - produtos
  - pecas
  - insumos
  - execution
aliases:
  - Products API
  - Peças e Suprimentos
---

# API — Peças e Insumos

**Serviço dono:** Execution Service (`/api/products`, MongoDB)

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

| Método | Rota | Perfis | Resposta |
|---|---|---|---|
| POST | `/api/products` | ADMIN, TECHNICIAN | 201 · 409 SKU já cadastrado · 400 dados inválidos |
| GET | `/api/products` | ADMIN, TECHNICIAN | 200 lista |
| GET | `/api/products/{id}` | ADMIN, TECHNICIAN | 200 · 404 |
| PUT | `/api/products/{id}` | ADMIN, TECHNICIAN | 200 · 404 · 409 SKU de outro produto |
| DELETE | `/api/products/{id}` | ADMIN, TECHNICIAN | 204 · 404 |

## POST /api/products · PUT /api/products/{id}

Mesmo corpo nas duas rotas (o PUT substitui os dados cadastrais):

```json
{ "name": "Óleo 5W30", "sku": "OLEO-5W30", "type": "SUPPLY", "unit": "LITER",
  "category": "Lubrificantes", "brand": "Mobil", "costPrice": 25.00, "salePrice": 45.00,
  "manufacturerCode": "MB-5W30", "warrantyMonths": 6, "fractionalAllowed": true, "packageSize": 1 }
```
- Obrigatórios: `name`, `sku`, `type`, `unit`, `salePrice`.
- `type`: `PART` (peça) ou `SUPPLY` (insumo). `unit`: `UNIT`, `LITER`, `MILLILITER`.
- `costPrice`, `salePrice` ≥ 0. O SKU é único.
- O PUT mantém `id`, `active` e `createdAt`; o estoque do produto não é alterado (use
  [[API - Estoque]]).

**200/201**
```json
{ "id": "665f...", "name": "Óleo 5W30", "sku": "OLEO-5W30", "type": "SUPPLY", "unit": "LITER",
  "category": "Lubrificantes", "brand": "Mobil", "costPrice": 25.00, "salePrice": 45.00, "active": true,
  "manufacturerCode": "MB-5W30", "warrantyMonths": 6, "fractionalAllowed": true, "packageSize": 1,
  "createdAt": "...", "updatedAt": "..." }
```

> [!note] Preço no orçamento
> O Billing copia nome, SKU, marca e `salePrice` para o item do orçamento no momento em que
> ele é gerado — mudar o preço depois não altera orçamentos já emitidos.

---

## Links Relacionados
- [[API - Estoque]]
- [[API - Orcamento]]
