---
title: Domínio DDD
tags:
  - regras
  - ddd
  - dominio
aliases:
  - DDD
  - Agregados
---

# Domínio DDD

Os bounded contexts do Event Storming viraram os limites dos microsserviços.

| Contexto (serviço) | Agregado | Entidades / VOs | Invariantes principais |
|---|---|---|---|
| **Ordem de Serviço** (os) | `ServiceOrder` | `WorkshopService` (serviço da OS), `Status` | transições do [[Ciclo de Vida da OS]]; documento normalizado; FINALIZADA só com serviços DONE |
| | `ServiceType` | — | nome normalizado, único e imutável; MO ≥ 0 |
| | `SagaState` | `SagaStep` | passo esperado por evento; só recomeça depois de `FALHOU` |
| **Cliente** (customer) | `Client` | `Document` (`Cpf`/`Cnpj`) | dígitos verificadores; documento único |
| | `Vehicle` | `LicensePlate`, `VehicleType` | placa antiga ou Mercosul; vinculado a um cliente |
| | `User` | `Role` | e-mail único; senha BCrypt; bloqueio após 5 erros |
| **Faturamento** (billing) | `Budget` | `BudgetItem` (PART/SUPPLY/LABOR) | um por OS; totais derivados dos itens |
| | `Payment` | `PaymentHistory`, `PaymentStatus` | valor > 0; transições PENDENTE → APROVADO/RECUSADO → ESTORNADO (estorno ainda sem gatilho no os-service) |
| **Execução** (execution) | `Product` | `ProductType`, `UnitOfMeasure` | SKU único; preço ≥ 0 |
| | `Stock` | `StockMovement`, `StockReservation` | disponível = quantidade − reservado; reserva tudo ou nada |

## Linguagem ubíqua

| Termo | Significado |
|---|---|
| OS | Ordem de serviço de um veículo de um cliente |
| Tipo de serviço | Item do catálogo (ex.: `TROCA_OLEO`) com MO padrão |
| Serviço da OS | Instância do tipo dentro de uma OS, com status próprio |
| Diagnóstico | Peças e MO definidas pelo mecânico; dispara a Saga |
| Reserva / baixa / liberação | Estoque separado, consumido ou devolvido |
| Orçamento | Peças + MO, aprovado ou recusado pelo cliente |
| Cobrança | Pagamento no Mercado Pago, referência `<OS>` ou `<OS>-N` |

Agregados não têm setters: o estado muda por métodos de negócio e fábricas
([[Padroes de Projeto]]).

## Links Relacionados
- [[Ciclo de Vida da OS]]
- [[Reserva de Estoque]]
- [[Orcamento]]
