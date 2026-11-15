---
title: Docker Compose
tags:
  - como-rodar
  - docker
  - compose
aliases:
  - Compose
  - docker-compose
---

# Docker Compose

Arquivo: `workbench-messaging/docker-compose.dev.yml`. Três níveis, por **profile**:

| Comando | Sobe |
|---|---|
| `docker compose -f docker-compose.dev.yml up -d` | **Infra**: LocalStack, 3 Postgres, MongoDB (replica set) |
| `… --profile app up -d --build` | Infra **+ plataforma**: `messaging-init`, 4 serviços e gateway |
| `zap/scan-platform.sh` (profile `scan`) | Scan DAST com OWASP ZAP — [[OWASP ZAP]] |

## Serviços

| Serviço | Imagem / build | Porta | Depende de |
|---|---|---|---|
| `localstack` | `localstack/localstack:3` (SNS, SQS, STS) | 4566 | — |
| `os-db`, `billing-db`, `customer-db` | `postgres:16` | 15432, 15433, 15434 | — |
| `execution-mongo` | `mongo:7` com `--replSet rs0` (transações) | 27017 | — |
| `messaging-init` | `hashicorp/terraform:1.9.8` — aplica o Terraform do repo no LocalStack e termina | — | localstack |
| `customer-service` | build `../workbench-customer-service` | 8081 | customer-db |
| `execution-service` | build `../workbench-execution-service` | 8083 | execution-mongo, messaging-init |
| `billing-service` | build `../workbench-billing-service` | 8082 | billing-db, messaging-init |
| `os-service` | build `../workbench-os-service` | 8080 | os-db, messaging-init, customer-service |
| `gateway` | `nginx:1.27-alpine` + `local-gateway/nginx.conf` | 8000 | os, billing, execution |

Todos os serviços têm healthcheck em `/actuator/health` e `depends_on` com
`service_healthy` / `service_completed_successfully`, então a ordem de subida é garantida.

## Decisões

- **Mesma topologia da AWS:** as filas, tópicos e DLQs vêm do mesmo Terraform
  (`main.tf`) usado no deploy — não há script paralelo que possa divergir.
- **Gateway local = API Gateway:** `/api/clients|vehicles|users` → customer,
  `/api/budgets|payments` → billing, `/api/products|stocks` → execution, o resto → os. O
  nginx não valida o JWT (na AWS isso é a Lambda authorizer), mas cada serviço valida.
- **Mongo com `directConnection=true`:** o replica set de 1 nó anuncia o hostname do container;
  conectar direto no primário evita depender desse nome.
- **Logs JSON** de cada serviço em `${WORKBENCH_LOG_DIR:-/tmp/workbench}` no host, para o
  Datadog Agent local coletar.
- **Pagamento:** `PAYMENT_PROVIDER=fake` por padrão; para o sandbox do Mercado Pago exporte
  `PAYMENT_PROVIDER=mercadopago` e `MP_ACCESS_TOKEN=TEST-...` antes do `up`.
- **Perfil `local`:** o compose define `SPRING_PROFILES_ACTIVE=local` nos 4 serviços. É ele
  que libera os valores de desenvolvimento (segredo do JWT, pagamento simulado, admin com
  `admin123`); fora dele os segredos são obrigatórios.
- **Containers como os pods do EKS:** usuário não-root (UID 10001), sistema de arquivos
  somente leitura com só `/tmp` gravável, sem capabilities (`cap_drop: ALL`) e
  `no-new-privileges`. Se um serviço tentar gravar fora de `/tmp`, o erro aparece aqui,
  antes de chegar ao cluster.

## Comandos úteis

```bash
docker compose -f docker-compose.dev.yml --profile app logs -f os-service
docker compose -f docker-compose.dev.yml --profile app up -d --build billing-service   # rebuild de um
docker compose -f docker-compose.dev.yml --profile app down -v                         # zera tudo
```

## Links Relacionados
- [[Quickstart]]
- [[Configuracao Docker]]
- [[Variaveis de Ambiente]]
