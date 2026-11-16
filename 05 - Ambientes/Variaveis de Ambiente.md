---
title: Variáveis de Ambiente
tags:
  - ambientes
  - configuracao
  - variaveis
aliases:
  - Env Vars
  - Variáveis
---

# Variáveis de Ambiente

Na AWS, os valores vêm do `k8s/configmap.yaml` e dos Secrets de cada serviço (injetados pelo
CD a partir dos GitHub Secrets).

> [!warning] Segredos não têm valor padrão
> `JWT_SECRET`, `SPRING_DATASOURCE_PASSWORD`, `PAYMENT_PROVIDER` (billing) e
> `ADMIN_INITIAL_PASSWORD` (customer) são obrigatórios: sem eles o serviço não sobe. Os valores
> de desenvolvimento ficam no perfil `local` (`application-local.yml` de cada serviço), que o
> compose do `workbench-messaging` ativa com `SPRING_PROFILES_ACTIVE=local`. Rodando pela IDE
> ou pelo Maven: `./mvnw spring-boot:run -Dspring-boot.run.profiles=local`.

## Comuns a todos os serviços

| Variável | Default | Descrição |
|---|---|---|
| `SERVER_PORT` | `8080` | Porta HTTP |
| `JWT_SECRET` | — (dev no perfil `local`) | HS256 — **o mesmo** em todos os serviços e na Lambda |
| `SPRING_PROFILES_ACTIVE` | — | `local` libera os valores de desenvolvimento |
| `SCHEDULING_POOL_SIZE` | `4` | Threads dos jobs `@Scheduled` (os, billing, execution) |
| `LOG_JSON_FILE` | `/tmp/workbench/<serviço>.log` | Arquivo de log JSON (coletado pelo Datadog Agent) |
| `DD_SERVICE` / `DD_ENV` / `DD_VERSION` | nome do serviço / `local` / `local` | Tags do Datadog (logs e métricas) |
| `DD_METRICS_ENABLED` | `false` | Liga o envio de métricas Micrometer → Datadog |
| `DD_API_KEY` / `DD_METRICS_URI` | — / `https://api.datadoghq.com` | Credencial e endpoint do Datadog |

## Banco

| Serviço | Variáveis | Default |
|---|---|---|
| os | `SPRING_DATASOURCE_URL`, `_USERNAME`, `_PASSWORD` | `jdbc:postgresql://localhost:15432/os_service`, `dbadmin`; senha sem padrão (dev no perfil `local`) |
| billing | idem | `jdbc:postgresql://localhost:15433/billing` |
| customer | idem | `jdbc:postgresql://localhost:15434/customer` |
| execution | `MONGODB_URI` | `mongodb://localhost:27017/execution` (na AWS, a URI `mongodb+srv://` do Atlas) |

## Mensageria (os, billing, execution)

| Variável | Default | Descrição |
|---|---|---|
| `MESSAGING_ENABLED` | `false` | Liga publicação/consumo SNS/SQS (sem ela a Saga não anda) |
| `AWS_REGION` | `us-east-1` | Região |
| `AWS_ENDPOINT` | — | `http://localhost:4566` (ou `http://localstack:4566` no compose); vazio na AWS |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | — | `test`/`test` no LocalStack; na AWS, credencial do pod |
| `ORDER_EVENTS_TOPIC_ARN`, `SAGA_REPLIES_QUEUE_URL`, `NOTIFICATIONS_TOPIC_ARN` | — | os-service |
| `BILLING_EVENTS_TOPIC_ARN`, `BILLING_COMMANDS_QUEUE_URL` | — | billing-service |
| `EXECUTION_EVENTS_TOPIC_ARN`, `EXECUTION_COMMANDS_QUEUE_URL` | — | execution-service |

No LocalStack: ARN `arn:aws:sns:us-east-1:000000000000:<tópico>` e URL
`http://<endpoint>:4566/000000000000/<fila>` (nomes no README do `workbench-messaging`).

## Específicas

| Serviço | Variável | Default | Descrição |
|---|---|---|---|
| os | `CUSTOMER_VALIDATION_ENABLED` | `false` | Valida cliente/placa no Customer Service ao abrir a OS |
| os | `CUSTOMER_SERVICE_URL` | — | Base URL do Customer (ex.: `http://customer-service:8080`) |
| customer | `ADMIN_INITIAL_PASSWORD` | — (obrigatório fora do perfil `local`) | Troca a senha do admin semeado no primeiro start (≥ 8 caracteres); sem ela, com o admin ainda em `admin123`, o serviço não sobe |
| billing | `PAYMENT_PROVIDER` | — (`fake` no perfil `local`) | `fake` (webhook simulado, só local/testes) ou `mercadopago` |
| billing | `MP_CONNECT_TIMEOUT` / `MP_READ_TIMEOUT` | `5s` / `10s` | Timeouts das chamadas ao Mercado Pago |
| os | `CUSTOMER_CONNECT_TIMEOUT` / `CUSTOMER_READ_TIMEOUT` | `2s` / `5s` | Timeouts das chamadas ao customer-service |
| billing | `MP_ACCESS_TOKEN` | — | Access Token do Mercado Pago. Os dois começam com `APP_USR-`: o que define sandbox ou produção é a credencial usada (*Credenciais de teste* × *de produção*), não o prefixo |
| billing | `MP_BASE_URL` | `https://api.mercadopago.com` | API do Mercado Pago |
| billing | `MP_NOTIFICATION_URL` | — | Opcional; a confirmação vem do job de consulta |
| billing | `PAYMENT_POLLING_INTERVAL_MS` | `30000` | Intervalo do job que consulta o pagamento |

> [!note] Removida
> `JWT_EXPIRATION` não existe mais nos serviços: eles só **validam** tokens. A expiração é
> definida na Lambda que emite o token.

## Lambda e gateway

- Lambda: `CUSTOMER_SERVICE_URL`, `JWT_SECRET`, `JWT_EXPIRATION` (README do `workbench-lambda`).
- Gateway (Terraform): `origin_url` (os) e `customer_origin_url`, `billing_origin_url`,
  `execution_origin_url` (README do `workbench-gateway`).

## Links Relacionados
- [[Configuracao Local]]
- [[Configuracao Docker]]
- [[JWT]]
