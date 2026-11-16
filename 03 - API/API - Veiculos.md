---
title: API — Veículos
tags:
  - api
  - veiculos
  - customer
aliases:
  - Vehicles API
---

# API — Veículos

**Serviço dono:** Customer Service (`/api/vehicles`, PostgreSQL)

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
| POST | `/api/vehicles` | ADMIN, TECHNICIAN | 201 · 404 cliente inexistente · 409 placa já cadastrada |
| GET | `/api/vehicles/{id}` | staff ou o dono | 200 · 403 · 404 |
| GET | `/api/vehicles/plate/{plate}` | staff ou o dono | 200 · 403 · 404 |
| GET | `/api/vehicles/client/{clientId}` | staff ou o dono | 200 lista |
| PUT | `/api/vehicles/{id}` | ADMIN, TECHNICIAN | 200 · 404 |
| DELETE | `/api/vehicles/{id}` | ADMIN, TECHNICIAN | 204 (desativa) |

## POST /api/vehicles

```json
{ "clientId": 1, "plate": "ABC-1234", "brand": "VW", "model": "Gol", "year": 2018, "color": "Prata", "type": "CAR" }
```
- Obrigatórios: `clientId`, `plate`, `brand`, `model`, `year` (≥ 1886), `type`.
- `type`: `CAR`, `MOTORCYCLE`, `TRUCK` ou `VAN`.
- A placa é validada (padrão antigo `ABC-1234` ou Mercosul `ABC1D23`) e devolvida formatada;
  marca, modelo e cor são gravados em maiúsculas.

**201**
```json
{ "id": 1, "clientId": 1, "plate": "ABC-1234", "brand": "VW", "model": "GOL", "year": 2018, "color": "PRATA",
  "type": "CAR", "active": true, "createdAt": "...", "updatedAt": "..." }
```

## PUT /api/vehicles/{id}

Mesmo corpo do POST, sem `clientId` (o veículo não troca de dono).

> [!note] Validação na abertura da OS
> O OS Service confere, por REST, que a placa existe e pertence ao CPF/CNPJ informado.

---

## Links Relacionados
- [[API - Clientes]]
- [[API - Ordens de Servico]]
