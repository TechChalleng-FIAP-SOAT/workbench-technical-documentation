---
title: API — Estoque
tags:
  - api
  - estoque
  - reservas
aliases:
  - Stock API
  - Estoque e Reservas
---

# API — Estoque

## Movimentações de Estoque — `/api/stocks`

### POST /api/stocks — Criar Registro de Estoque

Cria um registro de estoque para um produto (peça ou suprimento).

**Request Body:**
```json
{
  "productId": "uuid-da-peca",
  "quantity": 100,
  "minimumQuantity": 10
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "productId": "uuid-da-peca",
  "quantity": 100,
  "reservedQuantity": 0,
  "availableQuantity": 100,
  "minimumQuantity": 10
}
```

---

### GET /api/stocks — Listar Todo o Estoque

---

### GET /api/stocks/low — Estoque Abaixo do Mínimo

Retorna todos os produtos com `availableQuantity <= minimumQuantity`.

```json
[
  {
    "productId": "uuid",
    "productName": "Pastilha de Freio",
    "availableQuantity": 3,
    "minimumQuantity": 10
  }
]
```

---

### GET /api/stocks/product/{productId} — Estoque de um Produto

---

### PATCH /api/stocks/product/{productId}/entry — Entrada de Estoque

```json
{ "quantity": 50, "reason": "Compra de fornecedor" }
```

---

### PATCH /api/stocks/product/{productId}/exit — Saída de Estoque

```json
{ "quantity": 5, "reason": "Devolução com defeito" }
```

> [!danger] Validação de Negatividade
> Se `availableQuantity - quantity < 0`, a operação é rejeitada com erro 422.

---

### PATCH /api/stocks/product/{productId}/minimum — Atualizar Estoque Mínimo

```bash
PATCH /api/stocks/product/{productId}/minimum?minimumQuantity=20
```

---

### GET /api/stocks/product/{productId}/movements — Histórico de Movimentações

Retorna todos os registros de `StockMovement` ordenados por data.

```json
[
  {
    "type": "ENTRY",
    "quantity": 100,
    "reason": "Estoque inicial",
    "createdAt": "2024-01-15T10:00:00"
  },
  {
    "type": "RESERVATION",
    "quantity": 2,
    "reason": "Reserva para OS #abc",
    "createdAt": "2024-01-16T14:00:00"
  }
]
```

---

## Reservas de Estoque — `/api/stocks/reservations`

### POST /api/stocks/reservations — Reservar Estoque (ATÔMICO)

> [!danger] Operação Atômica
> Todos os itens são reservados ou nenhum. Se um produto tiver estoque insuficiente, toda a operação falha.

**Request Body:**
```json
{
  "serviceOrderId": "uuid-da-os",
  "items": [
    { "productId": "uuid-pastilha", "quantity": 2 },
    { "productId": "uuid-oleo", "quantity": 1.5 }
  ]
}
```

**Response 201:**
```json
{
  "serviceOrderId": "uuid-da-os",
  "reservations": [
    { "id": "uuid", "productId": "uuid-pastilha", "quantity": 2, "status": "ACTIVE" },
    { "id": "uuid", "productId": "uuid-oleo", "quantity": 1.5, "status": "ACTIVE" }
  ]
}
```

**Erros:**
| Código | Motivo |
|---|---|
| 422 | Estoque insuficiente para um ou mais produtos |
| 404 | Produto não encontrado |

---

### PATCH /api/stocks/reservations/service-order/{serviceOrderId}/confirm — Confirmar Reserva

Confirma o consumo do estoque (quando OS é Finalizada). Status das reservas: `ACTIVE` → `CONFIRMED`.

**Response 200**

---

### PATCH /api/stocks/reservations/service-order/{serviceOrderId}/release — Liberar Reserva

Cancela as reservas e devolve estoque (quando OS é rejeitada). Status: `ACTIVE` → `RELEASED`.

**Response 200**

---

### GET /api/stocks/reservations/service-order/{serviceOrderId} — Listar Reservas da OS

```json
[
  {
    "id": "uuid",
    "productId": "uuid",
    "productName": "Pastilha de Freio",
    "quantity": 2,
    "unitPrice": 125.00,
    "status": "ACTIVE"
  }
]
```

---

## Links Relacionados
- [[Reserva de Estoque]]
- [[API - Pecas e Suprimentos]]
- [[API - Ordens de Servico]]
- [[Orcamento]]
