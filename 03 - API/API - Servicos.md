---
title: API — Serviços
tags:
  - api
  - servicos
aliases:
  - Services API
---

# API — Serviços

> [!info] Serviço vs Ordem de Serviço
> Uma OS contém um ou mais **Serviços**. Cada serviço tem seu próprio status (`TO_DO → DOING → DONE`). A OS só pode ser finalizada quando todos os serviços estiverem `DONE`.

## POST /services — Criar Serviço para uma OS

**Request Body:**
```json
{
  "serviceOrderId": "uuid-da-os",
  "serviceTypeId": "uuid-do-tipo",
  "description": "Trocar pastilhas dianteiras e traseiras"
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "serviceOrderId": "uuid-da-os",
  "serviceType": { "id": "uuid", "name": "Freios" },
  "description": "Trocar pastilhas dianteiras e traseiras",
  "status": "TO_DO",
  "createdAt": "2024-01-15T10:00:00"
}
```

---

## GET /services — Listar Todos os Serviços

---

## GET /services/{id} — Buscar Serviço por ID

---

## GET /services/os/{idOS} — Listar Serviços de uma OS

```bash
GET /services/os/uuid-da-os
```

Retorna todos os serviços vinculados à OS informada.

---

## PATCH /services/update-status — Atualizar Status do Serviço

**Request Body:**
```json
{
  "serviceId": "uuid-do-servico",
  "status": "DOING"
}
```

**Transições válidas:**
```
TO_DO → DOING → DONE
```

> [!danger] Sem Volta
> Não é possível retroceder o status de um serviço. `DONE` é estado final.

**Response 200:** serviço atualizado

---

## GET /service-types — Listar Tipos de Serviço

Retorna os tipos de serviço cadastrados no sistema (ex: "Freios", "Motor", "Suspensão").

**Response 200:**
```json
[
  { "id": "uuid", "name": "Freios" },
  { "id": "uuid", "name": "Motor" },
  { "id": "uuid", "name": "Suspensão" },
  { "id": "uuid", "name": "Elétrica" }
]
```

---

## PUT /services/{id} — Atualizar Serviço

Permite alterar a descrição do serviço.

**Request Body:**
```json
{
  "description": "Descrição atualizada do serviço"
}
```

---

## Links Relacionados
- [[Ciclo de Vida da OS]]
- [[API - Ordens de Servico]]
- [[API - Monitoramento]]
