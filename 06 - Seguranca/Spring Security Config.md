---
title: Spring Security Config
tags:
  - seguranca
  - spring-security
aliases:
  - SecurityConfig
---

# Spring Security Config

Cada microsserviço tem a sua `infrastructure/security/SecurityConfig`, com o mesmo esqueleto:

- **Stateless**, CSRF desligado (API com Bearer, sem cookie de sessão).
- `JwtFilter` antes do `UsernamePasswordAuthenticationFilter` — [[JWT]].
- **401/403 em JSON** (`JsonSecurityErrorHandler`), formato `{timestamp, status, error}`.
- **Cabeçalhos:** `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`,
  `Cache-Control: no-store`, `Cross-Origin-Resource-Policy: same-origin`,
  `Cross-Origin-Opener-Policy: same-origin`, `Cross-Origin-Embedder-Policy: require-corp`
  (testados no `*IntegrationTest` de cada serviço).
- Públicos em todos: `/actuator/health/**`, `/swagger-ui/**`, `/v3/api-docs/**`.

## Regras por serviço

| Serviço | Público | Cliente (dono) + staff | Só staff (ADMIN/TECHNICIAN) |
|---|---|---|---|
| os | — | `GET /order/document/**`, `POST /order/*/decision`, `POST /order/*/payment-retry` | todo o resto |
| customer | `POST /api/users/auth/validate` (usado pela Lambda) | `GET /api/clients/**`, `GET /api/vehicles/**` | `GET /api/clients` (lista), escrita; `POST /api/users/signup` só **ADMIN** |
| billing | `POST /api/payments/webhook` (só com `PAYMENT_PROVIDER=fake`, que só sobe no perfil `local`) | `GET /api/budgets/**`, `GET /api/payments/**` | criação manual de cobrança |
| execution | — | — | tudo |

"Dono" é conferido no caso de uso (`Requester.requireAccessTo`): cliente acessando dado de
outro → **403**.

## Erros de requisição

O `GlobalExceptionHandler` de cada serviço responde 400 para UUID/JSON inválido, 404, 409
(conflito/duplicado), 422 (regra de negócio) e 500 genérico sem vazar detalhe interno — ver
[[Relatorio de Vulnerabilidades - Fase 4]].

## Links Relacionados
- [[JWT]]
- [[OWASP ZAP]]
- [[Autorizacao e Roles]]
