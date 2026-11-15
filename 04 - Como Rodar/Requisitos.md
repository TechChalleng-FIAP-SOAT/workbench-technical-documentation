---
title: Requisitos
tags:
  - como-rodar
  - requisitos
aliases:
  - Pré-requisitos
---

# Requisitos

## Para rodar local (compose)

| Ferramenta | Versão | Para quê |
|---|---|---|
| Docker + Docker Compose v2 | 24+ / 2.20+ | Plataforma inteira (`--profile app`) |
| ~6 GB de RAM livres para o Docker | — | 4 JVMs + 3 Postgres + Mongo + LocalStack |
| `curl` e `jq` | qualquer | Roteiro `SAGA-E2E-LOCAL.md` |
| Python 3 | 3.9+ | Gerar o token de dev ([[Quickstart]]) |

O Terraform que cria as filas roda **dentro** de um container (`messaging-init`); não precisa
estar instalado.

## Para desenvolver um serviço

| Ferramenta | Versão |
|---|---|
| Java (JDK) | **21** (Temurin ou Corretto) |
| Maven | wrapper `./mvnw` do repositório (não precisa instalar) |
| Docker | para os testes de integração (Testcontainers sobe Postgres/Mongo) |

Stack dos serviços: Spring Boot **4.0.9**, Spring Security 7, Flyway (Postgres), Spring Data
MongoDB (execution), AWS SDK v2 (SNS/SQS), Micrometer + Datadog, JUnit 5, Testcontainers,
Cucumber (os-service), JaCoCo.

## Para a AWS

Terraform ≥ 1.5, AWS CLI v2, `kubectl` e conta com permissão para EKS, RDS, Lambda, API
Gateway, SNS/SQS — passo a passo em `DEPLOY-AWS-GUIA.md`.

## Links Relacionados
- [[Quickstart]]
- [[Rodando Testes]]
