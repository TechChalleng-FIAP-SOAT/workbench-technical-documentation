---
title: Arquitetura Alvo (Microsserviços — Fase 4)
tags:
  - arquitetura
  - microsservicos
  - fase4
  - saga
---

# Arquitetura Alvo — Microsserviços (Fase 4)

Refatoração do monólito **workbench-monolith** para 4 microsserviços independentes com
banco próprio, mensageria assíncrona (SNS/SQS) e Saga orquestrada.

> Decisão formalizada em `workbench-monolith/docs/adr/ADR-0003-arquitetura-microsservicos-fase4.md`.

## Serviços

| Serviço | Bounded context | Migra do monólito | Banco |
|---|---|---|---|
| **Customer Service** | Clientes + veículos + validações + auth CPF | `client`, `vehicle` | PostgreSQL |
| **OS Service** | Ciclo de vida da OS + **orquestração da Saga** | `serviceorder`, `service` | PostgreSQL |
| **Billing Service** | Orçamento + pagamento (Mercado Pago) | `budget` + novo `payment` | PostgreSQL |
| **Execution Service** | Fila de execução + estoque + produtos | `stock`, `product` | MongoDB |

## Diagrama de componentes

```mermaid
flowchart TB
    client([Cliente])
    gw[API Gateway]
    lambda[Lambda Auth CPF]

    subgraph OS[OS Service - orquestrador]
      osdb[(PostgreSQL)]
    end
    subgraph CU[Customer Service]
      cudb[(PostgreSQL)]
    end
    subgraph BI[Billing Service]
      bidb[(PostgreSQL)]
    end
    subgraph EX[Execution Service]
      exdb[(MongoDB)]
    end

    mp[Mercado Pago]
    sns{{SNS topicos}}

    client --> gw
    gw --> lambda
    lambda -. valida cliente .-> CU
    gw --> OS

    OS <-->|comandos/eventos| sns
    CU <-->|eventos| sns
    BI <-->|comandos/eventos| sns
    EX <-->|comandos/eventos| sns

    OS -. valida cliente/veiculo REST .-> CU
    BI <-->|pagamento + webhook| mp
```

## Fluxo da Saga (orquestrada pelo OS Service)

```mermaid
sequenceDiagram
    participant OS as OS Service (orquestrador)
    participant EX as Execution
    participant BI as Billing
    participant MP as Mercado Pago

    OS->>EX: ComandoReservarEstoque
    EX-->>OS: ReservaConfirmada
    OS->>BI: ComandoGerarOrcamento
    BI-->>OS: OrcamentoGerado
    Note over OS: aguarda aprovacao do cliente
    OS->>BI: ComandoCobrarPagamento
    BI->>MP: cria pagamento
    MP-->>BI: webhook: aprovado
    BI-->>OS: PagamentoConfirmado
    OS->>OS: avanca para EM_EXECUCAO

    Note over OS,MP: Falha no pagamento →
    MP-->>BI: webhook: recusado
    BI-->>OS: PagamentoFalhou
    OS->>EX: ComandoLiberarReserva (compensacao)
    OS->>BI: ComandoCancelarOrcamento (compensacao)
    OS->>OS: reverte aprovacao
```

## Links Relacionados
- [[Visao Geral]]
- [[Contratos de Mensagem]]
- [[Convencoes Microsservicos]]
