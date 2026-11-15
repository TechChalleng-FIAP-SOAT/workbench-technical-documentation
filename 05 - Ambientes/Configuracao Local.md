---
title: Configuração Local
tags:
  - ambientes
  - local
  - desenvolvimento
aliases:
  - Dev Local
---

# Configuração Local

Dois jeitos de rodar na máquina:

| Jeito | Quando usar | Como |
|---|---|---|
| **Tudo no compose** | demo, teste ponta a ponta, scan de segurança | [[Quickstart]] (`--profile app`) |
| **Infra no compose + serviço na IDE** | depurar/alterar um serviço | abaixo |

## Infra no compose + serviço pelo Maven/IDE

```bash
cd workbench-messaging
docker compose -f docker-compose.dev.yml up -d      # LocalStack + bancos
./bootstrap-localstack.sh                            # tópicos e filas (Terraform → LocalStack)
```

Rode o serviço que você está mexendo com `./mvnw spring-boot:run` (ou pela IDE, classe
`*Application`). Os defaults do `application.yml` já apontam para a infra local
(`localhost:1543x`, `localhost:27017`); só a mensageria precisa ser ligada:

```bash
MESSAGING_ENABLED=true AWS_ENDPOINT=http://localhost:4566 \
AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test \
EXECUTION_EVENTS_TOPIC_ARN=arn:aws:sns:us-east-1:000000000000:workbench-execution-events \
EXECUTION_COMMANDS_QUEUE_URL=http://localhost:4566/000000000000/workbench-execution-commands-queue \
SERVER_PORT=8083 ./mvnw spring-boot:run
```
As variáveis de cada serviço estão no [[Saga Ponta a Ponta]] (Passo 3) e em
[[Variaveis de Ambiente]].

> [!tip] Misturar os dois
> Dá para deixar o compose com `--profile app` no ar e parar só o serviço que vai depurar
> (`docker compose … stop billing-service`), subindo-o pela IDE na mesma porta (8082).
> Use as URLs `localhost` em vez dos nomes dos containers.

## Banco

- **Postgres:** o Flyway aplica as migrations (`src/main/resources/db/migration`) no start.
  Cliente SQL: `localhost:15432` (os), `15433` (billing), `15434` (customer), usuário `dbadmin`.
- **MongoDB:** `mongodb://localhost:27017/execution`; índices criados no start
  (`auto-index-creation`).

## Links Relacionados
- [[Quickstart]]
- [[Variaveis de Ambiente]]
- [[Rodando Testes]]
