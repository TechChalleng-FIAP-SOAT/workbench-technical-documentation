---
title: API — Autenticação
tags:
  - api
  - autenticacao
  - jwt
aliases:
  - Login
  - Signup
---

# API — Autenticação

> [!info] Endpoints Públicos
> Estes endpoints **não requerem token JWT**. São os únicos acessíveis sem autenticação.

## POST /auth/login

Autentica um usuário e retorna o JWT para uso nas demais rotas.

**Request Body:**
```json
{
  "email": "superadmin@system.com",
  "password": "coxinha123"
}
```

**Response 200:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJzdXBlcmFkbWluQHN5c3..."
}
```

**Erros:**
| Código | Motivo |
|---|---|
| 401 | Credenciais inválidas |
| 400 | Campos obrigatórios ausentes |

**Exemplo curl:**
```bash
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"superadmin@system.com","password":"coxinha123"}'
```

---

## POST /signup

Cria um novo usuário no sistema.

> [!warning] Requer ROLE_ADMIN
> Apesar de estar em `/signup`, este endpoint exige que o criador seja ROLE_ADMIN. Não é um cadastro público.

**Request Body:**
```json
{
  "email": "tecnico@oficina.com",
  "password": "senha123",
  "role": "ROLE_TECHNICIAN"
}
```

**Response 201:**
```json
{
  "id": "uuid-do-usuario",
  "email": "tecnico@oficina.com",
  "roles": ["ROLE_TECHNICIAN"]
}
```

---

## Como Usar o Token

Após o login, inclua o token em todas as requisições:

```bash
# Substitua <TOKEN> pelo token recebido no login
curl -H "Authorization: Bearer <TOKEN>" \
     http://localhost:8080/api/clients
```

> [!tip] Validade do Token
> O token expira em **24 horas** (86400000ms). Após expirar, faça login novamente.

---

## Links Relacionados
- [[JWT]]
- [[Autorizacao e Roles]]
- [[Credenciais e Seeds]]
