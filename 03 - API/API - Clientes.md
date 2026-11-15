---
title: API — Clientes
tags:
  - api
  - clientes
  - customer
aliases:
  - Clients API
---

# API — Clientes

**Serviço dono:** Customer Service (`/api/clients`, PostgreSQL)

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
| POST | `/api/clients` | ADMIN, TECHNICIAN | 201 cliente · 409 documento já cadastrado · 400 CPF/CNPJ inválido |
| GET | `/api/clients` | ADMIN, TECHNICIAN | 200 lista |
| GET | `/api/clients/{id}` | staff ou o próprio cliente | 200 · 403 outro cliente · 404 |
| GET | `/api/clients/document/{document}` | staff ou o próprio cliente | 200 · 403 · 404 |
| PUT | `/api/clients/{id}` | ADMIN, TECHNICIAN | 200 · 404 |
| DELETE | `/api/clients/{id}` | ADMIN, TECHNICIAN | 204 (desativa — soft delete; o login por CPF passa a dar 403) |

## POST /api/clients

```json
{ "name": "Maria Oliveira", "document": "52998224725", "email": "maria@example.com", "phone": "11999990000" }
```
- `name` e `document` obrigatórios; `name` é gravado em maiúsculas.
- `document` aceita CPF ou CNPJ (com ou sem máscara) e é validado pelos dígitos verificadores.

**201**
```json
{ "id": 1, "name": "MARIA OLIVEIRA", "document": "52998224725", "email": "maria@example.com",
  "phone": "11999990000", "active": true, "createdAt": "...", "updatedAt": "..." }
```

## PUT /api/clients/{id}

```json
{ "name": "Maria Oliveira Souza", "email": "maria.souza@example.com", "phone": "11988887777" }
```
O documento não muda (é a chave usada pela OS e pelo login).

> [!note] Quem mais consulta
> O OS Service chama `GET /api/clients/document/{doc}` ao abrir a OS (cliente existe e
> está ativo) e para achar o e-mail da notificação; a Lambda chama para o login por CPF.
> Nenhum outro serviço lê o banco do Customer (ADR-0006).

---

## Links Relacionados
- [[API - Veiculos]]
- [[API - Ordens de Servico]]
- [[API - Autenticacao]]
