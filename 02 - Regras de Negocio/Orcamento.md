---
title: Orçamento
tags:
  - regras
  - orcamento
  - billing
aliases:
  - Budget
---

# Orçamento

**Dono:** billing-service. Gerado pela Saga, nunca à mão.

## Como nasce

1. Diagnóstico registrado no os-service → `ComandoReservarEstoque` ao Execution.
2. Execution reserva e responde `ReservaConfirmada` com os itens (nome, SKU, marca, tipo,
   preço de venda).
3. os-service envia `ComandoGerarOrcamento` com as **peças** (do Execution) e a **mão de obra**
   de cada serviço da OS com custo > 0.
4. Billing grava o `Budget` e publica `OrcamentoGerado` → OS em `AGUARDANDO_APROVACAO`.

## Cálculo

| Item | `itemType` | Valor |
|---|---|---|
| Peça / insumo | `PART` / `SUPPLY` | `quantidade × preço de venda` (preço copiado no momento) |
| Mão de obra | `LABOR` | custo do serviço na OS (informado no diagnóstico ou padrão do catálogo — ADR-0005) |

`totalParts` + `totalLabor` = `totalPrice`. Mudar o preço do produto depois não altera
orçamentos já emitidos.

## Decisão do cliente

- **Aprovar** → baixa de estoque e OS `APROVADO`.
- **Recusar** → compensação: reserva liberada, OS `RECUSADA` (pode ter novo diagnóstico).
- Falha ao gerar o orçamento: reenvio até 3 vezes; depois a reserva é liberada (compensação).

## Pagamento

Ao entrar em `PAGAMENTO_PENDENTE`, o Billing cria a cobrança no Mercado Pago (Checkout Pro) e
o link vai por e-mail. O `PaymentStatusPollingJob` confirma o pagamento (sem webhook público);
recusa permite nova cobrança (e avisa o cliente por e-mail). O billing sabe estornar um pagamento
aprovado (`ComandoEstornarPagamento`), mas o os-service ainda não envia esse comando: hoje nenhum
fluxo dispara estorno.

Rotas: [[API - Orcamento]].

## Links Relacionados
- [[Ciclo de Vida da OS]]
- [[Reserva de Estoque]]
