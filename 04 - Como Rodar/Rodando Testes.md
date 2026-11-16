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

## Teste ponta a ponta (plataforma no compose)
Com o compose no ar (`docker compose -f docker-compose.dev.yml --profile app up -d --build`, em
`workbench-messaging`), um script percorre a plataforma inteira pelo gateway: caminho feliz até
`ENTREGUE`, compensação por falta de estoque, pagamento recusado com nova cobrança, e 401/403.
```bash
cd workbench-messaging && e2e/saga-e2e.sh          # ~1 min; código 0 se tudo passou
e2e/saga-e2e.sh feliz estoque                       # cenários: feliz | estoque | pagamento | seguranca
```
Usa pagamento simulado (`PAYMENT_PROVIDER=fake`), não o Mercado Pago. Detalhes no README do
`workbench-messaging`. Não roda no CI.

## Cobertura

JaCoCo com **gate de 80% de linhas** no `verify` (o build falha abaixo disso). Relatório em
`target/site/jacoco/index.html`.

| Serviço | Linhas | Branches | Testes (15/11/2026) |
|---|---|---|---|
| os-service | 91,1% | 75,5% | 255 |
| execution-service | 89,0% | 78,6% | 71 |
| customer-service | 87,0% | 64,0% | 81 |
| billing-service | 87,2% | 72,7% | 85 |

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
