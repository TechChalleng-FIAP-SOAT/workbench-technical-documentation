---
title: Tecnologias
tags:
  - arquitetura
  - stack
aliases:
  - Stack
---

# Tecnologias

## Serviços (os, customer, billing, execution)

| Tecnologia | Versão | Uso |
|---|---|---|
| Java | 21 | Linguagem |
| Spring Boot | **4.0.9** (Spring 7.0, Spring Security 7.0) | Web, segurança, actuator, validação |
| PostgreSQL + Flyway | 16 | os, billing, customer (migrations versionadas) |
| MongoDB + Spring Data MongoDB | 7 (Atlas na AWS) | execution, com transações multidocumento (replica set) |
| AWS SDK v2 (SNS/SQS) | 2.29.1 | Mensageria da Saga |
| JJWT | 0.13.0 | Validação do JWT |
| springdoc-openapi | 3.0.2 | Swagger UI e `/v3/api-docs` |
| ShedLock | 5.16.0 | Jobs agendados únicos entre réplicas (os, billing) |
| logstash-logback-encoder | 8.1 | Logs JSON (Datadog) |
| Micrometer + Datadog | — | Métricas |
| MapStruct | 1.6.3 | Mapeamento (os-service) |
| Lombok | — | Boilerplate |

## Testes e qualidade

JUnit 5, Mockito, Testcontainers 1.20.4 (Postgres/Mongo), Cucumber 7.20.1 (BDD no os),
JaCoCo 0.8.14 (gate 80%), SonarCloud, OWASP ZAP (DAST), Trivy (SCA).

## Infra

| Peça | Tecnologia |
|---|---|
| Containers | Docker (multi-stage, `amazoncorretto:21-alpine`) |
| Orquestração | Kubernetes (EKS) com HPA |
| IaC | Terraform (repositórios `workbench-k8s-terraform`, `-database`, `-messaging`, `-gateway`, `-lambda`) |
| Entrada | AWS API Gateway (REST) + Lambdas Java 21 |
| Mensageria | SNS (fan-out) + SQS (uma fila por consumidor) + DLQ |
| Local | Docker Compose + LocalStack + nginx (gateway local) |
| CI/CD | GitHub Actions (branch protection na `main`) |
| Observabilidade | Datadog (logs, métricas, dashboards, monitores) |
| Pagamento | Mercado Pago Checkout Pro |

## Links Relacionados
- [[Visao Geral]]
- [[Requisitos]]
