---
title: API — Orçamento
tags:
  - api
  - orcamento
  - budget
---

# API — Orçamento

> [!info] Orçamento é Calculado Automaticamente
> Não há endpoint para **criar** orçamento manualmente. Ele é gerado e atualizado automaticamente quando reservas de estoque são criadas, confirmadas ou liberadas.

## GET /api/budgets/service-order/{serviceOrderId} — Consultar Orçamento

Retorna o orçamento atual de uma OS.

**Response 200:**
```json
{
  "id": "uuid",
  "serviceOrderId": "uuid-da-os",
  "status": "PENDING",
  "totalAmount": 375.90,
  "items": [
    {
      "id": "uuid",
      "productName": "Pastilha de Freio Dianteira",
      "quantity": 2,
      "unitPrice": 125.00,
      "subtotal": 250.00
    },
    {
      "id": "uuid",
      "productName": "Óleo Motor 5W30",
      "quantity": 2.5,
      "unitPrice": 45.90,
      "subtotal": 114.75
    }
  ],
  "createdAt": "2024-01-15T14:00:00",
  "updatedAt": "2024-01-15T14:30:00"
}
```

**Erros:**
| Código | Motivo |
|---|---|
| 404 | OS não encontrada ou sem orçamento |

---

## Status do Orçamento

| Status | Significado |
|---|---|
| `PENDING` | Aguardando aprovação do cliente |
| `APPROVED` | Aprovado pelo cliente |

---

## Orçamento nas Rotas de OS

O orçamento também é retornado inline nas rotas:
- `GET /order` — inclui `budget` em cada OS
- `GET /order/{id}` — inclui `budget` completo com itens
- `GET /api/clients/my-orders/{orderId}` — inclui orçamento para aprovação do cliente

---

## Links Relacionados
- [[Orcamento]]
- [[Reserva de Estoque]]
- [[API - Ordens de Servico]]
- [[API - Estoque]]
