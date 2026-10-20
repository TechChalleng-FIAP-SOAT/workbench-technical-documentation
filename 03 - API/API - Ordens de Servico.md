---
title: API — Ordens de Serviço
tags:
  - api
  - service-order
  - os
aliases:
  - Service Order API
  - OS
---

# API — Ordens de Serviço

## POST /order — Criar Ordem de Serviço

Cria uma nova OS com status inicial `RECEBIDA` e os serviços solicitados.

**Request Body:**
```json
{
  "vehicleId": "uuid-do-veiculo",
  "clientId": "uuid-do-cliente",
  "description": "Cliente relata barulho no freio dianteiro",
  "services": [
    { "serviceTypeId": "uuid-tipo-servico", "description": "Verificar e trocar pastilhas" }
  ]
}
```

**Response 201:**
```json
{
  "id": "uuid-da-os",
  "status": "RECEBIDA",
  "description": "Cliente relata barulho no freio dianteiro",
  "vehicle": { "plate": "ABC-1234", "model": "Civic" },
  "client": { "name": "João da Silva" },
  "services": [
    { "id": "uuid", "name": "Freios", "status": "TO_DO" }
  ],
  "budget": null,
  "createdAt": "2024-01-15T10:00:00"
}
```

---

## GET /order — Listar Ordens de Serviço

Retorna todas as OS com orçamento incluído.

**Response 200:**
```json
[
  {
    "id": "uuid",
    "status": "EM_DIAGNOSTICO",
    "vehicle": { "plate": "ABC-1234" },
    "budget": { "totalAmount": 350.00, "status": "PENDING" },
    "createdAt": "2024-01-15T10:00:00"
  }
]
```

---

## GET /order/{id} — Detalhe da OS

Retorna os detalhes completos: serviços, reservas de estoque e orçamento.

**Response 200:** objeto completo | **404:** não encontrada

---

## PATCH /order/{id} — Atualizar Status da OS

Avança o status da OS para o próximo estado.

**Request Body:**
```json
{
  "status": "EM_DIAGNOSTICO"
}
```

**Transições válidas:**
```
RECEBIDA → EM_DIAGNOSTICO
EM_DIAGNOSTICO → AGUARDANDO_APROVACAO
APROVADO → FINALIZADA          (requer todos serviços DONE)
FINALIZADA → ENTREGUE
```

> [!warning] Transição APROVADO
> A transição `AGUARDANDO_APROVACAO → APROVADO` é feita pelo cliente via portal:
> `PATCH /api/clients/my-orders/{orderId}/approve`

> [!danger] Regra de Finalização
> `APROVADO → FINALIZADA` só é permitido se **todos** os serviços da OS estiverem com status `DONE`. Caso contrário, retorna 422.

**Erros:**
| Código | Motivo |
|---|---|
| 404 | OS não encontrada |
| 422 | Transição inválida ou condição não satisfeita |

---

## Diagrama de Fluxo Completo

```mermaid
sequenceDiagram
    participant A as Atendente
    participant T as Técnico
    participant C as Cliente
    participant API

    A->>API: POST /order (RECEBIDA)
    T->>API: PATCH /order/{id} → EM_DIAGNOSTICO
    T->>API: POST /api/stocks/reservations
    Note over API: Budget calculado automaticamente
    T->>API: PATCH /order/{id} → AGUARDANDO_APROVACAO
    C->>API: GET /api/clients/my-orders/{id}
    C->>API: PATCH /api/clients/my-orders/{id}/approve (→ APROVADO)
    T->>API: PATCH /services/update-status (TO_DO → DOING → DONE)
    T->>API: PATCH /order/{id} → FINALIZADA
    Note over API: Reservas confirmadas; estoque debitado
    A->>API: PATCH /order/{id} → ENTREGUE
```

---

## Links Relacionados
- [[Ciclo de Vida da OS]]
- [[API - Servicos]]
- [[API - Estoque]]
- [[API - Clientes]]
- [[Orcamento]]
