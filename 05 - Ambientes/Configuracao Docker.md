---
title: Configuração — Ambiente Docker
tags:
  - ambientes
  - docker
  - configuracao
aliases:
  - Docker Environment
  - Container
---

# Configuração — Ambiente Docker

## Topologia (Tudo em Container)

```
Docker Network: workbench-monolith_default
├── postgres        (postgres:16)         → porta 5432 (interna)
├── app             (build local)         → porta 8080 (exposta)
├── validation      (curl)                → sem porta exposta
├── sonarqube_db    (postgres:16)         → sem porta exposta (interna)
├── sonarqube       (sonarqube:community) → porta 9000 (exposta)
└── zap             (zaproxy/zap-stable)  → sem porta exposta
```

---

## Habilitar o Serviço `app` no Docker

Por padrão o serviço `app` está comentado no `docker-compose.yml`. Para rodar tudo em Docker:

1. Descomente o serviço `app` no `docker-compose.yml`
2. Execute:
```bash
docker compose up -d --build
```

> [!warning] Rebuild Necessário
> Toda alteração no código requer rebuild da imagem: `docker compose build app`. Por isso o padrão é rodar a aplicação localmente.

---

## Comunicação Entre Serviços

Em Docker Compose, use o **nome do serviço** como hostname:

| De → Para | URL |
|---|---|
| `app` → `postgres` | `jdbc:postgresql://postgres:5432/workshop` |
| `validation` → `app` | `http://app:8080` |
| `zap` → `app` | `http://app:8080` |

> [!danger] Não use `localhost` em Docker Compose
> `localhost` dentro de um container se refere ao próprio container, não à máquina host. Use o nome do serviço do Docker Compose.

---

## Variáveis de Ambiente no Docker Compose

```yaml
services:
  app:
    build: .
    ports:
      - "8080:8080"
    environment:
      DB_URL: jdbc:postgresql://postgres:5432/workshop
      DB_USERNAME: user
      DB_PASSWORD: password
      JWT_SECRET: meu-segredo-seguro-aqui
      JWT_EXPIRATION: 86400000
    depends_on:
      postgres:
        condition: service_healthy
```

---

## Health Check do PostgreSQL

O serviço `app` só sobe após o banco estar saudável:

```yaml
postgres:
  image: postgres:16
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U user -d workshop"]
    interval: 5s
    timeout: 5s
    retries: 10
```

---

## Persistência de Dados

O PostgreSQL usa um volume Docker para persistir dados entre restarts:

```yaml
volumes:
  postgres_data:

services:
  postgres:
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sh:/docker-entrypoint-initdb.d/init.sh
```

> [!info] init.sh
> O `init.sh` só é executado quando o volume está vazio (primeira criação). Para forçar re-execução: `docker compose down -v`.

---

## Logs dos Serviços

```bash
# Todos os serviços
docker compose logs

# Serviço específico em tempo real
docker compose logs -f app
docker compose logs -f postgres
docker compose logs -f sonarqube
docker compose logs -f zap
```

---

## Troubleshooting

| Problema | Causa | Solução |
|---|---|---|
| App não conecta no banco | Banco ainda iniciando | Aguardar health check passar |
| `Connection refused :5432` | Container postgres não está rodando | `docker compose up -d postgres` |
| SonarQube sem memória | RAM insuficiente | Subir apenas postgres + app |
| Porta 8080 em uso | Outro processo usando a porta | Mudar `SERVER_PORT` ou matar o processo |

---

## Links Relacionados
- [[Docker Compose]]
- [[Variaveis de Ambiente]]
- [[Configuracao Local]]
- [[SonarQube]]
- [[OWASP ZAP]]
