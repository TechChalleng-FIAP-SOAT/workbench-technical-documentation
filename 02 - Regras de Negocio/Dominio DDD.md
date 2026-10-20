---
title: Domínio DDD
tags:
  - regras-negocio
  - ddd
  - domain
  - arquitetura
aliases:
  - Domain Model
  - DDD
---

# Domínio DDD

## Aggregate Roots

### Client (Aggregate Root)

Invariantes do domínio aplicadas no construtor:
- Nome é obrigatório
- CPF é validado e imutável após criação
- Email e telefone são opcionais mas validados

```java
// Criação (novo cliente)
Client.create(name, cpf, email, phone)

// Reconstituição (carga do banco)
Client.reconstitute(id, name, cpf, email, phone, active, createdAt)
```

> [!info] Por que dois métodos de criação?
> `create()` garante invariantes e gera UUID. `reconstitute()` aceita dados já validados vindos do banco, sem re-validar. Separar os dois previne bugs onde a reconstituição dispara regras de negócio que não se aplicam a dados persistidos.

### Stock (Aggregate Root)

Controla quantidade disponível e previne negatividade:

```java
stock.addQuantity(10)          // entrada
stock.removeQuantity(5)        // saída (lança exceção se insuficiente)
stock.reserve(3, osId)         // reserva (lança exceção se disponível < 3)
stock.availableQuantity()      // quantity - reservedQuantity
stock.isLowStock()             // availableQuantity <= minimumQuantity
```

## Value Objects

### Cpf

Valida o CPF (formato e dígitos verificadores). Aceita com ou sem formatação:

```java
new Cpf("529.982.247-25")   // válido
new Cpf("52998224725")      // válido (sem formatação)
new Cpf("111.111.111-11")   // lança InvalidCpfException
```

## Entities

### ServiceOrder

Entidade com máquina de estados explícita:

```java
enum ServiceOrderStatus {
    RECEBIDA, EM_DIAGNOSTICO, AGUARDANDO_APROVACAO,
    APROVADO, FINALIZADA, ENTREGUE
}
```

### StockReservation

Rastreia reservas vinculadas a uma OS:

```java
enum ReservationStatus { ACTIVE, CONFIRMED, RELEASED }
```

### StockMovement

Log imutável de todas as movimentações de estoque. Nunca é deletado.

## Domain Events

| Evento | Publicado por | Ouvido por | Efeito |
|---|---|---|---|
| `ReservationChangedEvent` | StockHandler | BudgetHandler | Recalcula orçamento da OS |

```java
// Publicação
applicationEventPublisher.publishEvent(
    new ReservationChangedEvent(serviceOrderId)
);

// Listener
@EventListener
public void handle(ReservationChangedEvent event) {
    budgetRecalculateHandler.handle(event.serviceOrderId());
}
```

## Repository Pattern (Ports & Adapters)

O domínio define **interfaces** (ports). A infraestrutura fornece **implementações** (adapters):

```java
// Port (domínio — sem dependência de Spring/JPA)
public interface ClientRepository {
    Optional<Client> findById(UUID id);
    Optional<Client> findByCpf(Cpf cpf);
    Client save(Client client);
    List<Client> findAll();
}

// Adapter (infra — depende de Spring Data JPA)
@Repository
public class ClientJpaRepository implements ClientRepository {
    private final ClientJpaRepositoryInterface jpa;
    private final ClientMapper mapper;
    // ...
}
```

## Soft Delete

Entidades com soft delete (`Client`, `Vehicle`, `Part`, `Supply`) nunca são removidas do banco:

- Flag `active = false` indica registro inativo
- Queries sempre incluem `WHERE active = true`
- Histórico preservado para auditoria

## Links Relacionados
- [[Padroes de Projeto]]
- [[Reserva de Estoque]]
- [[Ciclo de Vida da OS]]
- [[Estrutura de Pastas]]
