---
title: API — Veículos
tags:
  - api
  - veiculos
aliases:
  - Endpoints de Veículo
---

# API — Veículos

> [!info] Roles Necessárias
> Todos os endpoints requerem `ROLE_ADMIN` ou `ROLE_TECHNICIAN`.

## POST /api/vehicles — Criar Veículo

Veículo deve ser vinculado a um cliente existente.

**Request Body:**
```json
{
  "clientId": "uuid-do-cliente",
  "plate": "ABC-1234",
  "brand": "Honda",
  "model": "Civic",
  "year": 2020,
  "color": "Prata"
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "clientId": "uuid-do-cliente",
  "plate": "ABC-1234",
  "brand": "Honda",
  "model": "Civic",
  "year": 2020,
  "color": "Prata",
  "active": true
}
```

---

## GET /api/vehicles/{id} — Buscar por ID

**Response 200:** objeto veículo | **404:** não encontrado

---

## GET /api/vehicles/plate/{plate} — Buscar por Placa

```bash
GET /api/vehicles/plate/ABC-1234
```

Útil para identificar rapidamente o veículo na entrada da oficina.

---

## GET /api/vehicles/client/{clientId} — Listar Veículos do Cliente

Retorna todos os veículos ativos vinculados ao cliente.

**Response 200:**
```json
[
  { "id": "uuid", "plate": "ABC-1234", "brand": "Honda", "model": "Civic", ... },
  { "id": "uuid", "plate": "XYZ-5678", "brand": "Toyota", "model": "Corolla", ... }
]
```

---

## PUT /api/vehicles/{id} — Atualizar Veículo

Permite alterar cor, modelo, ano. **Placa é imutável.**

**Request Body:**
```json
{
  "brand": "Honda",
  "model": "Civic EX",
  "year": 2021,
  "color": "Preto"
}
```

---

## DELETE /api/vehicles/{id} — Desativar Veículo (Soft Delete)

Marca como `active = false`. **Não remove do banco.**

**Response 204** (sem corpo)

---

## Links Relacionados
- [[API - Clientes]]
- [[API - Ordens de Servico]]
- [[Dominio DDD]]
