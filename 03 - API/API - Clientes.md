---
title: API — Clientes
tags:
  - api
  - clientes
aliases:
  - Endpoints de Cliente
---

# API — Clientes

> [!info] Autenticação Necessária
> Todos os endpoints requerem `Authorization: Bearer <token>` exceto onde indicado.

## CRUD de Clientes

### POST /api/clients — Criar Cliente

**Roles:** ROLE_ADMIN, ROLE_TECHNICIAN

**Request Body:**
```json
{
  "name": "João da Silva",
  "cpf": "529.982.247-25",
  "email": "joao@email.com",
  "phone": "11999999999"
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "name": "João da Silva",
  "cpf": "529.982.247-25",
  "email": "joao@email.com",
  "phone": "11999999999",
  "active": true
}
```

> [!warning] CPF é imutável
> Após criar o cliente, o CPF não pode ser alterado.

---

### GET /api/clients — Listar Clientes

**Roles:** ROLE_ADMIN, ROLE_TECHNICIAN

Retorna apenas clientes com `active = true`.

**Response 200:**
```json
[
  { "id": "uuid", "name": "João da Silva", "cpf": "...", ... },
  { "id": "uuid", "name": "Maria Souza", "cpf": "...", ... }
]
```

---

### GET /api/clients/{id} — Buscar por ID

**Response 200:** objeto cliente | **404:** não encontrado

---

### GET /api/clients/cpf/{cpf} — Buscar por CPF

```bash
GET /api/clients/cpf/529.982.247-25
GET /api/clients/cpf/52998224725  # sem formatação também funciona
```

---

### PUT /api/clients/{id} — Atualizar Cliente

Permite alterar nome, email e telefone. **CPF é imutável.**

**Request Body:**
```json
{
  "name": "João Silva Atualizado",
  "email": "novo@email.com",
  "phone": "11888888888"
}
```

---

### DELETE /api/clients/{id} — Desativar Cliente (Soft Delete)

Marca o cliente como `active = false`. **Não remove do banco.**

**Response 204** (sem corpo)

---

## Portal do Cliente

Endpoints para uso do próprio cliente (ROLE_USER) — retornam apenas dados do usuário autenticado.

### GET /api/clients/my-orders — Minhas OS

**Roles:** ROLE_USER, ROLE_ADMIN, ROLE_TECHNICIAN

Retorna lista de ordens de serviço do cliente autenticado.

**Response 200:**
```json
[
  {
    "id": "uuid",
    "status": "AGUARDANDO_APROVACAO",
    "createdAt": "2024-01-15T10:00:00",
    "vehicle": { "plate": "ABC-1234", "model": "Civic" },
    "budget": { "totalAmount": 350.00, "status": "PENDING" }
  }
]
```

---

### GET /api/clients/my-orders/{orderId} — Detalhe da OS

Retorna detalhes completos da OS + serviços + orçamento itemizado.

**Response 200:**
```json
{
  "id": "uuid",
  "status": "AGUARDANDO_APROVACAO",
  "services": [
    { "name": "Troca de pastilha", "status": "TO_DO" }
  ],
  "budget": {
    "totalAmount": 350.00,
    "items": [
      { "productName": "Pastilha de Freio", "quantity": 2, "unitPrice": 125.00, "subtotal": 250.00 }
    ]
  }
}
```

---

### PATCH /api/clients/my-orders/{orderId}/approve — Aprovar OS

Aprova o orçamento. OS transita de `AGUARDANDO_APROVACAO` → `APROVADO`.

**Response 200** | **409:** OS não está aguardando aprovação

---

## Links Relacionados
- [[Ciclo de Vida da OS]]
- [[Autorizacao e Roles]]
- [[API - Veiculos]]
- [[Orcamento]]
