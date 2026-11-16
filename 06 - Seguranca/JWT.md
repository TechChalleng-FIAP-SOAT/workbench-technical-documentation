---
title: JWT — Autenticação
tags:
  - seguranca
  - jwt
aliases:
  - Token
---

# JWT — Autenticação

**Assinatura assimétrica (RS256).** Quem emite tem a chave **privada**; quem só verifica tem a
**pública** e não consegue emitir token. Antes era HS256 com o mesmo segredo em 5 componentes:
quem tivesse o segredo (qualquer serviço comprometido) emitia token de ADMIN para todos.

| Quem | Chave | Faz o quê |
|---|---|---|
| `workbench-lambda` — login de cliente (`POST /auth`) e de staff (`POST /auth/login`) | privada `JWT_PRIVATE_KEY` | **Emite** os tokens, com `kid=workbench-auth` |
| Lambda authorizer (API Gateway) | pública `JWT_PUBLIC_KEY` | Verifica antes de qualquer rota protegida |
| os, billing, customer, execution (`JwtFilter`) | pública `JWT_PUBLIC_KEY` | Verificam de novo (defesa em profundidade) |
| os-service → customer-service (token de serviço) | privada `JWT_SERVICE_PRIVATE_KEY` (os) e pública `JWT_SERVICE_PUBLIC_KEY` (**só o customer**) | O os emite, com `kid=os-service`; só o customer aceita |

O cabeçalho `kid` diz qual chave verifica o token. `kid` desconhecido, token HS256 ou chave de
outro serviço são recusados (401). O token de serviço do os-service **não** vale no billing, no
execution nem no gateway: comprometer o os-service não dá acesso de ADMIN aos outros.

| Token | `sub` | Claims | Authority no serviço |
|---|---|---|---|
| Cliente | CPF/CNPJ | `clientId`, `roles: ["CLIENT"]` | `ROLE_CLIENT` |
| Staff | e-mail | `roles: ["ADMIN"]` ou `["TECHNICIAN"]`, sem `clientId` | `ROLE_ADMIN` / `ROLE_TECHNICIAN` |
| Serviço (os → customer) | `os-service` | `roles: ["ADMIN","TECHNICIAN"]`, 1 min | gerado pelo `ServiceTokenProvider` |

## Validação nos serviços (`JwtFilter`)

1. Lê `Authorization: Bearer <token>`.
2. Escolhe a chave pelo `kid` e confere assinatura e expiração (`JwtService.tryParseClaims`).
3. Token com `clientId` → `ROLE_CLIENT`; senão, as `roles` da claim viram `ROLE_*`.
4. Token ausente ou inválido não autentica: a rota protegida responde **401 em JSON**
   (`JsonSecurityErrorHandler`). Perfil sem permissão → **403 em JSON**.

O dono do recurso (cliente só vê a própria OS, orçamento, cadastro…) é conferido nos casos de
uso via `Requester`, não só pela role. Expiração: definida na Lambda (`JWT_EXPIRATION`,
padrão 24 h).

## Formato das chaves

RSA 2048. Na configuração, cada chave é o **Base64 do DER numa linha só** (a pública em X.509,
a privada em PKCS#8); o PEM inteiro também é aceito. Para gerar os dois pares da AWS:

```bash
for par in auth service; do
  openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out $par.pem
  openssl pkcs8 -topk8 -nocrypt -in $par.pem -outform DER | base64 | tr -d '\n' > $par-private.b64
  openssl pkey -in $par.pem -pubout -outform DER | base64 | tr -d '\n' > $par-public.b64
done
# auth-private.b64 → JWT_PRIVATE_KEY      auth-public.b64 → JWT_PUBLIC_KEY
# service-private.b64 → JWT_SERVICE_PRIVATE_KEY   service-public.b64 → JWT_SERVICE_PUBLIC_KEY
shred -u *.pem 2>/dev/null || rm -P *.pem   # não deixe a chave privada no disco
```

> [!warning] Chaves privadas
> `JWT_PRIVATE_KEY` só é usada pelo CD do `workbench-lambda`, e `JWT_SERVICE_PRIVATE_KEY`
> só pelo pipeline do `workbench-os-service`. Nos secrets da organização, restrinja cada uma
> a esse repositório (*Repository access → Selected repositories*).

## Gerar um token de dev

Local não há Lambda. O par de **desenvolvimento** é gerado **por máquina** por
`workbench-messaging/scripts/dev-keys.sh` (a primeira chamada de `dev-jwt.sh` já o cria) e fica
em `workbench-messaging/dev-keys/`, **fora do git**. A pública vai para o `.env` que o compose lê:

```bash
cd workbench-messaging
bash -c 'source scripts/dev-jwt.sh; mint_dev_jwt "{\"sub\":\"admin@workbench.dev\",\"roles\":[\"ADMIN\"],\"exp\":4102444800}"'
```
Token de cliente: troque as claims por `{"sub":"52998224725","clientId":1,"roles":["CLIENT"],"exp":...}`.
Cole o token na variável `token` do environment **Workbench - Local** do Postman (ele vem vazio).

## Trocar as chaves
Ver o [[Runbook]] (seção "Trocar as chaves do JWT").

## Links Relacionados
- [[Spring Security Config]]
- [[API - Autenticacao]]
- [[Variaveis de Ambiente]]
- ADR-0009 (`workbench-monolith/docs/adr`) — por que RS256
