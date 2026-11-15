---
title: Reserva de Estoque
tags:
  - regras
  - estoque
  - execution
aliases:
  - Estoque
  - Reservas
---

# Reserva de Estoque

**Dono:** execution-service (MongoDB, transação multidocumento).

## Saldo

```
availableQuantity = quantity − reservedQuantity
lowStock          = availableQuantity ≤ minimumQuantity
```

## Ciclo da reserva

| Momento | Comando da Saga | Efeito | Reserva |
|---|---|---|---|
| Diagnóstico | `ComandoReservarEstoque` | reservado += qtd (peça continua na prateleira) | `ACTIVE` |
| Orçamento aprovado | `ComandoConfirmarReserva` | quantidade −= qtd, reservado −= qtd (baixa) | `CONFIRMED` |
| Recusa / falha no orçamento | `ComandoLiberarReserva` | reservado −= qtd (volta ao disponível) | `RELEASED` |

## Regras

- **Tudo ou nada:** valida todos os itens antes de reservar; faltou um → nada é reservado e a
  resposta é `ReservaFalhou` com o motivo (OS fica em diagnóstico, ver [[Ciclo de Vida da OS]]).
- **Idempotente por OS:** se já existe reserva `ACTIVE` da OS, o comando repetido devolve a
  mesma; confirmação e liberação também são idempotentes.
- Saldo, reserva e movimentação (`StockMovement`: ENTRY, EXIT, RESERVATION…) gravados na
  **mesma transação**.
- Saída manual (`PATCH .../exit`) só usa o disponível — não consome o que está reservado.

Rotas: [[API - Estoque]].

## Links Relacionados
- [[Orcamento]]
- [[Dominio DDD]]
