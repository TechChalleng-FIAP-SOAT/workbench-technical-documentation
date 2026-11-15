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

> **Fonte de verdade executável:** `workbench-messaging/contracts/saga-messages.json`.
> Cada serviço da Saga tem um teste de contrato (`*SagaContractTest`) que lê uma cópia
> desse arquivo — se o código divergir da tabela, o `mvn verify` falha. Esta tabela
> reflete o contrato implementado (versão 1, 28/10/2026).

| Tipo | Emissor → Consumidor | Payload (obrigatórios; *opcionais em itálico*) | Efeito |
|---|---|---|---|
| `ComandoReservarEstoque` | OS → Execution | `items[]: {productId, quantity}` | reserva atômica (idempotente por OS) |
| `ReservaConfirmada` | Execution → OS | `reservations`, `parts[]: {productId, quantity, name, itemType, unitPrice, *sku*, *brand*}` | OS pede orçamento |
| `ReservaFalhou` | Execution → OS | `reason` | Saga → FALHOU |
| `ComandoGerarOrcamento` | OS → Billing | `parts[]` (repassa as do Execution), `labor[]: {serviceName, laborCost, *laborCode*}`, `customerDocument` | gera orçamento (snapshot) |
| `OrcamentoGerado` | Billing → OS | `budgetId`, `totalParts`, `totalLabor`, `totalPrice` | OS → `AGUARDANDO_APROVACAO` |
| `OrcamentoFalhou` | Billing → OS | `reason` | reenvia até 3×; depois compensa (`ComandoLiberarReserva`) |
| `ComandoConfirmarReserva` | OS → Execution | — | baixa de estoque (na aprovação) |
| `ReservaBaixada` | Execution → OS | `reservations` | limpa pendência |
| `ComandoLiberarReserva` | OS → Execution | — | devolve estoque (recusa/falha) |
| `ReservaLiberada` | Execution → OS | `reservations` | Saga → FALHOU (compensação concluída) |
| `ComandoCobrarPagamento` | OS → Billing | — | cria cobrança no Mercado Pago (idempotente) |
| `CobrancaCriada` | Billing → OS | `gatewayPaymentId`, `checkoutUrl` | e-mail com link de pagamento |
| `PagamentoConfirmado` | Billing → OS | — | OS → `PAGO` → `ENTREGUE` |
| `PagamentoFalhou` | Billing → OS | `reason` | OS retida em `PAGAMENTO_PENDENTE` |
| `ComandoEstornarPagamento` | OS → Billing | — | estorno (*ainda não enviado pelo OS*) |
| `PagamentoEstornado` | Billing → OS | `status` | (*ainda não tratado pelo OS*) |

> Nomes de mensagem ficam em português por serem **dados do contrato** trafegados entre
> serviços; no código, as constantes têm nome em inglês (`SagaMessages.RESERVE_STOCK =
> "ComandoReservarEstoque"`). Cada evento só é aceito no passo da Saga em que é esperado.

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
