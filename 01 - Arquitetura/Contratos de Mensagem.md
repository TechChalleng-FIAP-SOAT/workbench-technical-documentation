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

> **Idempotência obrigatória**: SQS entrega *at-least-once*. Todo consumidor precisa
> aguentar a mesma mensagem duas vezes: os participantes são idempotentes (reservar, baixar,
> liberar, gerar orçamento e cobrar de novo dão o mesmo resultado) e o orquestrador só aceita
> cada evento no passo esperado. O dedupe por `messageId` em memória é só uma otimização.

## Envelope comum

Todas as mensagens compartilham o mesmo envelope:

```json
{
  "messageId": "uuid",         // único por mensagem (dedupe)
  "sagaId": "uuid",            // rodada da Saga (muda a cada novo diagnóstico) — ver abaixo
  "serviceOrderId": "uuid",    // OS alvo
  "type": "ComandoReservarEstoque",
  "occurredAt": "2026-10-02T12:00:00Z",
  "payload": { }               // específico do tipo (abaixo)
}
```

**`sagaId` = rodada da Saga.** O orquestrador gera um `sagaId` novo a cada início ou novo
diagnóstico e põe esse valor em todo comando. **O participante devolve o `sagaId` que
recebeu**; o orquestrador descarta resposta com `sagaId` de outra rodada (reentrega antiga
do SQS). `PagamentoConfirmado` e `PagamentoFalhou` não respondem a um comando — saem do job
de consulta ao Mercado Pago ou do webhook simulado —, por isso o billing grava o `sagaId` do
`ComandoCobrarPagamento` na cobrança e publica o resultado com ele (ADR-0008). Para seguir
uma OS por todas as rodadas, use `serviceOrderId`.

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

- **Repetição e atraso:** o orquestrador aceita cada evento só no passo esperado e só da
  rodada atual (`sagaId`); os participantes são idempotentes. O dedupe por `messageId` é em
  memória, por réplica — uma otimização, não a garantia.
- **DLQ** por fila após N tentativas (sugestão: 3) — mensagens na DLQ exigem inspeção manual.
- **Estado da Saga** persistido no OS Service (tabela `saga_state`) para sobreviver a quedas.
- Comandos de compensação são sempre **idempotentes** (liberar reserva já liberada = no-op).

## Links Relacionados
- [[Arquitetura Alvo Microsservicos]]
- [[Convencoes Microsservicos]]
