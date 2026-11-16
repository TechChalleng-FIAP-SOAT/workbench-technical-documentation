---
title: Padrões de Projeto
tags:
  - arquitetura
  - padroes
aliases:
  - Design Patterns
---

# Padrões de Projeto

## Arquitetura hexagonal (ADR-0004), em cada serviço

```
domain/          regras de negócio puras (agregados, value objects, exceções de domínio)
application/     casos de uso + port/out (interfaces que o caso de uso precisa)
adapter/in/web   controllers REST + DTOs
adapter/out      implementações das portas (persistência)
infrastructure/  config, segurança, mensageria, clientes HTTP, jobs
```
A dependência aponta para dentro: `domain` não conhece Spring nem banco.

## Convenções de código

| Convenção | Como |
|---|---|
| **Uma classe por caso de uso** | `CreateServiceTypeUseCase`, `UpdateProductUseCase`… com um método `execute` |
| **DTOs fora do controller** | `<Recurso>Dtos` (records) ou um arquivo por DTO; o controller só traduz HTTP ↔ caso de uso |
| **Agregados sem setters** | estado muda por métodos de negócio (`advanceTo`, `moveTo`, `reserve`, `approve`, `replaceDetailsWith`) e fábricas (`create`, `reconstitute`) |
| **Idioma** | código em inglês; mensagens de erro ao cliente em português |
| **Erros** | exceções de domínio mapeadas no `GlobalExceptionHandler` (400/404/409/422); catch-all 500 genérico |

## Padrões usados

| Padrão | Onde |
|---|---|
| **Saga orquestrada** | `SagaOrchestrator` (os-service) com `SagaState` persistido, compensação e reenvio por timeout |
| **Ports & Adapters** | `*Repository`, `*Port` em `application/.../port/out` |
| **Factory method** | `ServiceOrder.create`, `Payment.create`, `ServiceType.create`, `StockReservation.activate` |
| **Value Object** | `Cpf`, `Cnpj`, `Document`, `LicensePlate` (customer) |
| **State machine** | `OrderServiceStatusEnum.canTransitionTo`, `ServiceStatusEnum` (TO_DO→DOING→DONE) |
| **Idempotência** | dedupe por `messageId` nos consumidores SQS; guarda de passo esperado na Saga; reserva única por OS |
| **After-commit** | `AfterCommit.run` para notificar só depois da transação |
| **Polling job** | `PaymentStatusPollingJob` (Mercado Pago) com ShedLock |
| **Contract testing** | `*SagaContractTest` contra `contracts/saga-messages.json` |

## Links Relacionados
- [[Estrutura de Pastas]]
- [[Convencoes Microsservicos]]
- [[Dominio DDD]]
