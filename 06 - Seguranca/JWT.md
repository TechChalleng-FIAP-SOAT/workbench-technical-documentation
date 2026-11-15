---
title: JWT — Autenticação
tags:
  - seguranca
  - jwt
aliases:
  - Token
---

# JWT — Autenticação

**Quem emite:** só a `workbench-lambda` (`POST /auth` para cliente por CPF, `POST /auth/login`
para staff). **Quem valida:** a Lambda authorizer no API Gateway e, de novo, cada
microsserviço (`JwtFilter`). Todos usam HS256 com o **mesmo `JWT_SECRET`**.

| Token | `sub` | Claims | Authority no serviço |
|---|---|---|---|
| Cliente | CPF/CNPJ | `clientId`, `roles: ["CLIENT"]` | `ROLE_CLIENT` |
| Staff | e-mail | `roles: ["ADMIN"]` ou `["TECHNICIAN"]`, sem `clientId` | `ROLE_ADMIN` / `ROLE_TECHNICIAN` |
| Serviço (os → customer) | `os-service` | `roles: ["ADMIN","TECHNICIAN"]`, 1 min | gerado pelo `ServiceTokenProvider` |

## Validação nos serviços (`JwtFilter`)

1. Lê `Authorization: Bearer <token>`.
2. Confere assinatura e expiração (`JwtService.tryParseClaims` / `isExpired`).
3. Token com `clientId` → `ROLE_CLIENT`; senão, as `roles` da claim viram `ROLE_*`.
4. Token ausente ou inválido não autentica: a rota protegida responde **401 em JSON**
   (`JsonSecurityErrorHandler`). Perfil sem permissão → **403 em JSON**.

O dono do recurso (cliente só vê a própria OS, orçamento, cadastro…) é conferido nos casos de
uso via `Requester`, não só pela role. Expiração: definida na Lambda (`JWT_EXPIRATION`,
padrão 24 h); os serviços não emitem token e não têm essa variável.

## Gerar um token de dev

Local não há Lambda. Com o `JWT_SECRET` de dev:

```bash
python3 - <<'PY'
import base64,hashlib,hmac,json,time
b=lambda x: base64.urlsafe_b64encode(x).rstrip(b'=').decode()
n=int(time.time()); h=b(json.dumps({"alg":"HS256","typ":"JWT"}).encode())
p=b(json.dumps({"sub":"admin@workbench.dev","roles":["ADMIN"],"iat":n,"exp":n+86400}).encode())
s=b(hmac.new(b"akmsdkmasfnjsgknakmsdkmasdkmsadfkmdsakmdkmsadsa",f"{h}.{p}".encode(),hashlib.sha256).digest())
print(f"{h}.{p}.{s}")
PY
```
Token de cliente: troque o payload por `{"sub":"52998224725","clientId":1,"roles":["CLIENT"],...}`.

> [!warning] Na AWS o `JWT_SECRET` vem dos GitHub Secrets (nunca o default de dev).

## Links Relacionados
- [[Spring Security Config]]
- [[API - Autenticacao]]
- [[Variaveis de Ambiente]]
