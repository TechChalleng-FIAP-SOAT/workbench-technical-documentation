---
title: Rodando Testes
tags:
  - como-rodar
  - testes
  - cobertura
aliases:
  - Testes
  - Cobertura
---

# Rodando Testes

Cada serviço roda seus testes com o wrapper, dentro do próprio repositório:

```bash
./mvnw verify          # unit + integração + contrato (+ BDD no os) + gate de cobertura 80%
./mvnw test            # só os unitários (rápido, sem Docker)
```

O `verify` precisa de **Docker** rodando (Testcontainers sobe Postgres ou MongoDB).

## Tipos de teste

| Tipo | Onde | Exemplos |
|---|---|---|
| Unitário (domínio e casos de uso) | `src/test/java/.../domain`, `.../application` | regras de transição da OS, `SagaState`, reserva de estoque |
| Controller (MockMvc standalone) | `.../adapter/in/web` | códigos HTTP, validação, mensagens de erro |
| Integração | `.../integration/*IntegrationTest` (failsafe) | API real + banco real via Testcontainers, cabeçalhos de segurança |
| Contrato da Saga | `.../contract/*SagaContractTest` | mensagens publicadas e consumidas batem com `contracts/saga-messages.json` |
| BDD (Cucumber) | os-service: `src/test/resources/features/*.feature` | ciclo de vida da OS em português |

Surefire roda os unitários; failsafe roda os `*IntegrationTest` (e o BDD).

## Cobertura

JaCoCo com **gate de 80% de linhas** no `verify` (o build falha abaixo disso). Relatório em
`target/site/jacoco/index.html`.

| Serviço | Linhas | Branches | Testes (11/11/2026) |
|---|---|---|---|
| os-service | 89,8% | 72,0% | 222 |
| execution-service | 88,7% | 76,5% | 67 |
| customer-service | 86,6% | 62,8% | 76 |
| billing-service | 85,6% | 71,9% | 66 |

No CI, o job `unit-test` publica o relatório como artefato `jacoco-report` e o job
`code-analysis` envia a cobertura ao SonarCloud ([[SonarQube]]).

## Contrato da Saga

A fonte única é `workbench-messaging/contracts/saga-messages.json`. Depois de mudar o
contrato, copie para os serviços:

```bash
cd workbench-messaging && scripts/sync-saga-contract.sh          # copia
scripts/sync-saga-contract.sh --check                             # só confere
```
O CI dos 3 serviços da Saga falha se a cópia divergir da `main` do `workbench-messaging`.

## Links Relacionados
- [[SonarQube]]
- [[Requisitos]]
