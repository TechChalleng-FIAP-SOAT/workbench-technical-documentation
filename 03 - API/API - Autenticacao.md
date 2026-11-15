---
title: API — Autenticação
tags:
  - api
  - autenticacao
  - jwt
  - lambda
aliases:
  - Login
  - Auth
---

# API — Autenticação

**Serviço dono:** `workbench-lambda` (emissão) + Customer Service (credenciais de staff)

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

> [!warning] Só existe na AWS
> O login é feito pelas Lambdas atrás do API Gateway. Localmente não há Lambda: gere um
> JWT de dev assinado com o `JWT_SECRET` padrão (o `SAGA-E2E-LOCAL.md` traz um pronto e o
> `workbench-messaging/zap/zap-scan.sh` mostra como assinar um).

## POST /auth — Login do cliente (CPF/CNPJ) · público

```json
{ "cpf": "529.982.247-25" }
```

| Status | Corpo | Quando |
|---|---|---|
| 200 | `{ "token": "...", "expiresIn": 86400000, "client": { "id": 1, "name": "MARIA OLIVEIRA" } }` | cliente existe e está ativo |
| 400 | `{ "error": "Invalid CPF" }` | documento ausente ou dígitos inválidos |
| 403 | `{ "error": "Client is inactive" }` | cliente desativado |
| 404 | `{ "error": "Client not found" }` | documento sem cadastro |

Token do cliente: `sub` = documento, claim `clientId`, `roles: ["CLIENT"]`. O cliente só
enxerga as **próprias** OS, orçamentos, pagamentos, cadastro e veículos (dono conferido
em cada caso de uso — `Requester`).

## POST /auth/login — Login de staff (e-mail/senha) · público

```json
{ "email": "admin@workbench.dev", "password": "admin123" }
```

| Status | Corpo | Quando |
|---|---|---|
| 200 | `{ "token": "...", "expiresIn": 86400000, "email": "...", "roles": ["ADMIN"] }` | credenciais válidas |
| 400 | `{ "error": "Email and password are required" }` | campos ausentes |
| 401 | `{ "error": "Invalid credentials" }` | senha errada **ou** e-mail bloqueado (5 erros seguidos → 15 min) |

A Lambda valida as credenciais em `POST /api/users/auth/validate` do Customer Service
(rota interna, sem token) e emite o JWT de staff (sem `clientId`).

## POST /api/users/signup — Cadastrar usuário staff · ADMIN

```json
{ "email": "tecnico@workbench.dev", "password": "senha-forte", "roles": ["TECHNICIAN"] }
```
**201** `{ "id": 2, "email": "tecnico@workbench.dev", "roles": ["TECHNICIAN"] }` · **409** e-mail já cadastrado.

## Perfis

| Role | Quem | Pode |
|---|---|---|
| `ADMIN` | gestor | tudo |
| `TECHNICIAN` | mecânico/atendente | tudo, exceto cadastrar staff |
| `CLIENT` | dono do veículo (login por CPF) | consultar as próprias OS/orçamento/pagamento/cadastro, aprovar/recusar orçamento, refazer pagamento |

---

## Links Relacionados
- [[JWT]]
- [[Spring Security Config]]
- [[API - Clientes]]
