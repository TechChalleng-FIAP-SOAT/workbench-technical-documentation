---
title: Autorização e Roles
tags:
  - regras
  - seguranca
  - roles
aliases:
  - RBAC
  - Perfis
---

# Autorização e Roles

| Role | Quem | Como obtém o token |
|---|---|---|
| `ADMIN` | gestor da oficina | `POST /auth/login` (e-mail/senha) |
| `TECHNICIAN` | mecânico / atendente | `POST /auth/login` |
| `CLIENT` | dono do veículo | `POST /auth` (CPF/CNPJ) — token com claim `clientId` |

## O que cada um pode

| Ação | ADMIN | TECHNICIAN | CLIENT |
|---|---|---|---|
| Cadastrar staff (`/api/users/signup`) | ✅ | — | — |
| Clientes, veículos (escrita), catálogo de serviços, produtos, estoque | ✅ | ✅ | — |
| Abrir OS, diagnóstico, avançar status, executar serviços, monitoramento | ✅ | ✅ | — |
| Consultar o próprio cadastro, veículos, OS, orçamento, pagamento | ✅ | ✅ | ✅ só os **dele** |
| Aprovar/recusar orçamento, pedir nova cobrança | ✅ | ✅ | ✅ só da **própria** OS |

## Regra de dono

A role libera a rota; o **caso de uso** confere o dono pelo documento do token
(`Requester.requireAccessTo`). Cliente pedindo dado de outro documento → **403**
"Acesso negado". Staff passa direto.

Implementação por serviço: [[Spring Security Config]].

## Links Relacionados
- [[JWT]]
- [[API - Autenticacao]]
