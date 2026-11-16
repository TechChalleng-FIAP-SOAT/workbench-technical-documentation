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

> Decisão formalizada em `workbench-monolith/docs/adr/ADR-0006-arquitetura-microsservicos-fase4.md`.

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
    BI <-->|cobrança + consulta de pagamento| mp
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
    Note over OS: aguarda aprovacao do cliente (pausa humana)
    OS->>EX: ComandoConfirmarReserva (baixa de estoque)
    EX-->>OS: ReservaBaixada
    Note over OS: execução do serviço → FINALIZADA → PAGAMENTO_PENDENTE
    OS->>BI: ComandoCobrarPagamento
    BI->>MP: cria preferência (link de pagamento)
    BI-->>OS: CobrancaCriada (link por e-mail ao cliente)
    loop a cada 30 s
        BI->>MP: consulta o pagamento da OS
    end
    BI-->>OS: PagamentoConfirmado (mesmo sagaId da cobrança)
    OS->>OS: OS → PAGO → ENTREGUE

    Note over OS,MP: Pagamento recusado →
    BI-->>OS: PagamentoFalhou
    Note over OS: a OS fica em PAGAMENTO_PENDENTE, sem estorno de estoque (o serviço já foi executado).<br/>O cliente é avisado por e-mail e pede nova cobrança (payment-retry)
```

## Links Relacionados
- [[Visao Geral]]
- [[Contratos de Mensagem]]
- [[Convencoes Microsservicos]]
