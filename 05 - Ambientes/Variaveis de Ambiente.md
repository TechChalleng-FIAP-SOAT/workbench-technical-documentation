---
title: Variáveis de Ambiente
tags:
  - ambientes
  - configuracao
  - env
aliases:
  - Environment Variables
  - Envs
---

# Variáveis de Ambiente

## Referência Completa

| Variável | Padrão | Descrição | Obrigatória em Prod? |
|---|---|---|---|
| `DB_URL` | `jdbc:postgresql://localhost:5432/workshop` | URL de conexão com o banco | Sim |
| `DB_USERNAME` | `user` | Usuário do banco de dados | Sim |
| `DB_PASSWORD` | `password` | Senha do banco de dados | Sim |
| `JWT_SECRET` | `akmsdkmasfnjsgknakmsdkmasdkmsadfkmdsakmdkmsadsa` | Chave secreta para assinar os tokens JWT | **Sim — altere obrigatoriamente** |
| `JWT_EXPIRATION` | `86400000` | Duração do token em milissegundos (padrão: 24h) | Não |
| `SERVER_PORT` | `8080` | Porta da aplicação | Não |

---

## Configuração no `application.yml`

```yaml
spring:
  datasource:
    url: ${DB_URL:jdbc:postgresql://localhost:5432/workshop}
    username: ${DB_USERNAME:user}
    password: ${DB_PASSWORD:password}
  jpa:
    hibernate:
      ddl-auto: update
    packages-to-scan: com.os
    properties:
      hibernate:
        dialect: org.hibernate.dialect.PostgreSQLDialect
        format_sql: true

server:
  port: ${SERVER_PORT:8080}

jwt:
  secret: ${JWT_SECRET:akmsdkmasfnjsgknakmsdkmasdkmsadfkmdsakmdkmsadsa}
  expiration: ${JWT_EXPIRATION:86400000}
```

> [!info] Sintaxe `${VAR:default}`
> Spring Boot usa `${NOME_VARIAVEL:valor_padrão}`. Se a variável de ambiente não estiver definida, o valor após `:` é usado. Isso permite rodar localmente sem definir nenhuma variável.

---

## Por Ambiente

### Desenvolvimento Local
Nenhuma variável precisa ser definida — os valores padrão funcionam com o Docker Compose local.

### Docker Compose
O `docker-compose.yml` define as variáveis no serviço `app`:
```yaml
app:
  environment:
    - DB_URL=jdbc:postgresql://postgres:5432/workshop
    - DB_USERNAME=user
    - DB_PASSWORD=password
    - JWT_SECRET=meu-segredo-docker
    - JWT_EXPIRATION=86400000
```

> [!warning] `localhost` vs nome do serviço
> Em Docker Compose, use o **nome do serviço** (`postgres`) como host, não `localhost`. Containers se comunicam pela rede interna do Docker.

### Produção
```bash
export DB_URL=jdbc:postgresql://prod-db.host:5432/workshop
export DB_USERNAME=prod_user
export DB_PASSWORD=SenhaForte123!
export JWT_SECRET=$(openssl rand -base64 64)  # gera segredo aleatório
export JWT_EXPIRATION=28800000  # 8 horas (mais seguro)
```

---

## Sobre o JWT_SECRET

> [!danger] Nunca use o segredo padrão em produção
> O segredo padrão `akmsdkmasfnjsgknakmsdkmasdkmsadfkmdsakmdkmsadsa` é público (está no código). Qualquer pessoa pode forjar tokens com ele.

**Gere um segredo seguro:**
```bash
# Linux/Mac
openssl rand -base64 64

# Node.js
node -e "console.log(require('crypto').randomBytes(64).toString('base64'))"
```

**Requisitos:** mínimo 256 bits (32 bytes) para HS256.

---

## `ddl-auto` por Ambiente

| Ambiente | Valor Recomendado | Motivo |
|---|---|---|
| Desenvolvimento | `update` | Atualiza schema automaticamente |
| Testes | `create-drop` | Recria a cada execução |
| Produção | `validate` | Não altera o schema; valida apenas |

> [!danger] `ddl-auto: update` em Produção
> Nunca use `update` em produção — pode alterar o schema de forma inesperada. Use migrations (Flyway/Liquibase) para gerenciar o schema em produção.

---

## Links Relacionados
- [[Configuracao Local]]
- [[Configuracao Docker]]
- [[JWT]]
- [[Quickstart]]
