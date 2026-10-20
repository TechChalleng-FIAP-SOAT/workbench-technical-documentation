---
title: Configuração — Ambiente Local
tags:
  - ambientes
  - local
  - desenvolvimento
aliases:
  - Dev Local
  - Desenvolvimento
---

# Configuração — Ambiente Local

## Topologia

```
Sua máquina:
├── JVM → Spring Boot App (porta 8080)
└── Docker
    └── PostgreSQL 16 (porta 5432)
```

A aplicação roda diretamente na JVM (sem Docker) e se conecta ao PostgreSQL que roda em Docker.

---

## Setup Inicial

```bash
# 1. Sobe apenas o banco
docker compose up -d postgres

# 2. Aguarda estar pronto (opcional)
docker compose exec postgres pg_isready -U user -d workshop

# 3. Roda a aplicação
./mvnw spring-boot:run
```

---

## Configuração Padrão (sem variáveis)

O `application.yml` tem defaults que funcionam com o Docker Compose local:

```
DB URL:      jdbc:postgresql://localhost:5432/workshop
DB User:     user
DB Pass:     password
JWT Secret:  akmsdkmasfnjsgknakmsdkmasdkmsadfkmdsakmdkmsadsa
JWT Expiry:  86400000 (24h)
Port:        8080
```

Nenhuma variável de ambiente precisa ser definida para desenvolvimento local.

---

## Habilitar Logging SQL (Debug)

Adicione ao `application.yml` ou crie `application-local.yml`:

```yaml
spring:
  jpa:
    show-sql: true
    properties:
      hibernate:
        format_sql: true

logging:
  level:
    org.hibernate.SQL: DEBUG
    org.hibernate.type.descriptor.sql: TRACE
```

Ative o profile local:
```bash
./mvnw spring-boot:run -Dspring-boot.run.profiles=local
```

---

## Acessos Locais

| Recurso | URL |
|---|---|
| API Base | `http://localhost:8080` |
| Swagger UI | `http://localhost:8080/swagger-ui/index.html` |
| OpenAPI JSON | `http://localhost:8080/v3/api-docs` |
| PostgreSQL | `localhost:5432` (workshop / user / password) |

---

## Conectar ao Banco Localmente

```bash
# Via psql dentro do container
docker compose exec postgres psql -U user -d workshop

# Via cliente externo (DBeaver, DataGrip, etc.)
Host: localhost
Port: 5432
Database: workshop
User: user
Password: password
```

---

## Dados de Teste Pré-carregados

O `init.sh` popula o banco automaticamente. Se precisar recriar:

```bash
# Destrói o volume e recria
docker compose down -v
docker compose up -d postgres
```

Veja os dados disponíveis em: [[Credenciais e Seeds]]

---

## Links Relacionados
- [[Quickstart]]
- [[Variaveis de Ambiente]]
- [[Configuracao Docker]]
- [[Credenciais e Seeds]]
