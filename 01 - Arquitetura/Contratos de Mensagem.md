---
title: Contratos de Mensagem (Saga)
tags:
  - arquitetura
  - mensageria
  - saga
  - fase4
---

# Contratos de Mensagem — Saga da Ordem de Serviço

Mensagens que trafegam no broker **SNS → SQS** para coordenar a Saga orquestrada
pelo OS Service. Duas categorias:

- **Comando** (`Comando*`): o orquestrador (OS Service) pede a um serviço que execute algo.
- **Evento** (`*` no passado): um serviço informa um fato consumado.

> **Idempotência obrigatória**: SQS entrega *at-least-once*. Todo consumidor deve
> deduplicar por `messageId` + `sagaId`.

## Envelope comum

Todas as mensagens compartilham o mesmo envelope:

```json
{
  "messageId": "uuid",         // único por mensagem (dedupe)
  "sagaId": "uuid",            // correlaciona todos os passos de uma Saga
  "serviceOrderId": "uuid",    // OS alvo
  "type": "ComandoReservarEstoque",
  "occurredAt": "2026-10-02T12:00:00Z",
  "payload": { }               // específico do tipo (abaixo)
}
```

## Tabela de contratos

| Tipo | Direção | Emissor → Consumidor | Payload (campos) | Dispara | Compensação |
|---|---|---|---|---|---|
| `ComandoReservarEstoque` | Comando | OS → Execution | `items[]: {productId, quantity}` | reserva atômica no estoque | `ComandoLiberarReserva` |
| `ReservaConfirmada` | Evento | Execution → OS | `reservationIds[]` | OS pede orçamento | — |
| `ReservaFalhou` | Evento | Execution → OS | `reason`, `missing[]: {productId, faltante}` | aborta Saga | — |
| `ComandoGerarOrcamento` | Comando | OS → Billing | `reservationIds[]` | gera orçamento (snapshot de preço) | `ComandoCancelarOrcamento` |
| `OrcamentoGerado` | Evento | Billing → OS | `budgetId`, `totalPrice` | OS → `AGUARDANDO_APROVACAO` | — |
| `ComandoCobrarPagamento` | Comando | OS → Billing | `budgetId` (após aprovação do cliente) | cria pagamento no Mercado Pago | `ComandoEstornarPagamento` |
| `PagamentoConfirmado` | Evento | Billing → OS | `paymentId`, `amount` | OS → `EM_EXECUCAO` | — |
| `PagamentoFalhou` | Evento | Billing → OS | `paymentId`, `reason` | OS dispara compensações | — |
| `ComandoLiberarReserva` | Comando (comp.) | OS → Execution | `reservationIds[]` | libera reservas ACTIVE | — (idempotente) |
| `ComandoCancelarOrcamento` | Comando (comp.) | OS → Billing | `budgetId` | cancela orçamento | — (idempotente) |
| `ComandoEstornarPagamento` | Comando (comp.) | OS → Billing | `paymentId` | estorno no Mercado Pago | — (idempotente) |
| `OSFinalizada` | Evento | Execution → OS | `serviceOrderId` | OS → `FINALIZADA` | — |

## Pontos de falha e compensações

| Falha em | Estado parcial a desfazer | Compensações disparadas (ordem inversa) |
|---|---|---|
| Reserva de estoque | nada ainda confirmado | aborta: OS → status de falha |
| Geração de orçamento | reservas ativas | `ComandoLiberarReserva` |
| Pagamento | reservas + orçamento | `ComandoLiberarReserva` + `ComandoCancelarOrcamento` + reverte aprovação |
| Pós-pagamento (execução) | reservas + orçamento + pagamento | + `ComandoEstornarPagamento` |

## Regras

- **Dedupe** por (`sagaId`, `type`) ou `messageId` persistido por consumidor.
- **DLQ** por fila após N tentativas (sugestão: 3) — mensagens na DLQ exigem inspeção manual.
- **Estado da Saga** persistido no OS Service (tabela `saga_state`) para sobreviver a quedas.
- Comandos de compensação são sempre **idempotentes** (liberar reserva já liberada = no-op).

## Links Relacionados
- [[Arquitetura Alvo Microsservicos]]
- [[Convencoes Microsservicos]]
