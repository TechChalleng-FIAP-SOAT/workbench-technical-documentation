---
title: Quickstart — Subir o Projeto
tags:
  - como-rodar
  - quickstart
  - setup
aliases:
  - Como Rodar
  - Setup
---

# Quickstart — Subir o Projeto

A plataforma são **4 microsserviços** (os, customer, billing, execution) + mensageria
(SNS/SQS) + 4 bancos. Localmente tudo sobe com **um** `docker compose`, sem AWS e sem custo.

> [!info] Repositórios lado a lado
> O compose fica em `workbench-messaging` e faz o build dos serviços a partir das pastas
> irmãs (`../workbench-os-service`, `../workbench-customer-service`, …). Clone os
> repositórios na mesma pasta pai.

## 1. Subir tudo (≈ 3–5 min no primeiro build)

```bash
cd workbench-messaging
docker compose -f docker-compose.dev.yml --profile app up -d --build
docker compose -f docker-compose.dev.yml --profile app ps      # tudo "healthy"
```

| Porta | O quê |
|---|---|
| `8000` | **Gateway local** (nginx) — mesmo roteamento do API Gateway da AWS |
| `8080` · `8081` · `8082` · `8083` | os · customer · billing · execution (acesso direto) |
| `4566` | LocalStack (SNS/SQS) |
| `15432` · `15433` · `15434` · `27017` | Postgres os · billing · customer · MongoDB execution |

Swagger de cada serviço: `http://localhost:<porta>/swagger-ui/index.html`.

## 2. Token de acesso

Localmente não existe a Lambda de login: gere um JWT de ADMIN assinado com o `JWT_SECRET`
de dev (ver [[JWT#Gerar um token de dev]]):

```bash
export TOKEN=$(python3 - <<'PY'
import base64,hashlib,hmac,json,time
b=lambda x: base64.urlsafe_b64encode(x).rstrip(b'=').decode()
n=int(time.time()); h=b(json.dumps({"alg":"HS256","typ":"JWT"}).encode())
p=b(json.dumps({"sub":"admin@workbench.dev","roles":["ADMIN"],"iat":n,"exp":n+86400}).encode())
s=b(hmac.new(b"akmsdkmasfnjsgknakmsdkmasdkmsadfkmdsakmdkmsadsa",f"{h}.{p}".encode(),hashlib.sha256).digest())
print(f"{h}.{p}.{s}")
PY
)
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/service-types
```

## 3. Testar o fluxo

- **Passo a passo da Saga (curl):** `SAGA-E2E-LOCAL.md` na raiz do workspace.
- **Postman/Bruno:** `postman/workbench-plataforma.postman_collection.json` — aponte
  `osUrl`, `customerUrl`, `billingUrl` e `executionUrl` para `http://localhost:8000`.

## 4. Derrubar

```bash
docker compose -f docker-compose.dev.yml --profile app down       # mantém os dados
docker compose -f docker-compose.dev.yml --profile app down -v    # apaga os bancos
```

## Alternativa: só a infra + serviços pelo Maven

Para depurar um serviço na IDE: suba só a infra (`docker compose -f docker-compose.dev.yml up -d`,
sem profile), rode `./bootstrap-localstack.sh` para criar as filas e suba cada serviço com
`./mvnw spring-boot:run` e as variáveis do `SAGA-E2E-LOCAL.md` (Passo 3).

## Links Relacionados
- [[Requisitos]]
- [[Docker Compose]]
- [[Variaveis de Ambiente]]
- [[Credenciais e Seeds]]
