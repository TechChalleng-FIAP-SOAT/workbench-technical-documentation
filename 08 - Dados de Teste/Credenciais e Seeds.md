---
title: Credenciais e Dados de Teste
tags:
  - dados-teste
  - seeds
  - credenciais
aliases:
  - Test Data
  - Seeds
  - Dados Iniciais
---

# Credenciais e Dados de Teste

> [!info] Como são carregados
> Por **migrations Flyway** de cada serviço Postgres, no start (idempotentes). O MongoDB do
> execution começa vazio — produtos e estoques são criados pela API.

## Usuário staff (customer-service)

| Campo | Valor |
|---|---|
| E-mail | `admin@workbench.dev` |
| Senha | `admin123` só no perfil `local`; fora dele, a de `ADMIN_INITIAL_PASSWORD` |
| Role | `ADMIN` |
| Origem | `workbench-customer-service/.../db/migration/V2__users.sql` |

Com `ADMIN_INITIAL_PASSWORD` (≥ 8 caracteres) o serviço troca a senha no primeiro start
(`AdminPasswordInitializer`). Fora do perfil `local`, sem ela o serviço **não sobe** enquanto o
admin continuar com `admin123`; no perfil `local` (compose) só loga um aviso. Na AWS, defina-a
nos secrets da org (a pipeline também a exige).

Login (só na AWS, pela Lambda): `POST {gatewayUrl}/auth/login` com
`{"email":"admin@workbench.dev","password":"..."}`. Local: gere um token de dev
([[JWT#Gerar um token de dev]]). Mais usuários: `POST /api/users/signup` (ADMIN).

## Tipos de serviço (os-service)

Seed em `V2__seed_service_types.sql` (custo de MO 0 até alguém ajustar):

| Nome | Descrição |
|---|---|
| `TROCA_OLEO` | Troca de óleo e filtro |
| `ALINHAMENTO` | Alinhamento e balanceamento |
| `REVISAO` | Revisão geral preventiva |

Novos tipos: `POST /service-types` ([[API - Servicos]]).

## Massa sugerida para demo

| Dado | Valor | Observação |
|---|---|---|
| Cliente | `52998224725` (CPF válido), "Maria Oliveira" | `POST /api/clients` |
| Cliente 2 | `11144477735` (CPF válido) | para testar acesso de outro dono (403) |
| Veículo | placa `ABC-1234`, `type: CAR`, `year: 2018` | `POST /api/vehicles` |
| Produto | `OLEO-5W30`, `SUPPLY`, `LITER`, venda 45,00 | `POST /api/products` |
| Estoque | 100 unidades, mínimo 10 | `POST /api/stocks` |

O roteiro completo (com os comandos) está no [[Saga Ponta a Ponta]] e na pasta "Fluxo Saga" da
collection `postman/workbench-plataforma.postman_collection.json`.

## Pagamento de teste

- Local (`PAYMENT_PROVIDER=fake`): confirme com `POST /api/payments/webhook`
  `{"gatewayPaymentId":"<id>","approved":true}` — sem token.
- Sandbox do Mercado Pago: `MP_ACCESS_TOKEN=TEST-...` e pague o `checkoutUrl` com um cartão
  de teste do Mercado Pago (o job de consulta confirma em até 30 s).

## Links Relacionados
- [[Quickstart]]
- [[API - Autenticacao]]
- [[JWT]]
