---
title: API — Ordens de Serviço
tags:
  - api
  - os
  - saga
aliases:
  - Service Orders API
  - OS API
---

# API — Ordens de Serviço

**Serviço dono:** OS Service (`/order`, PostgreSQL) — orquestrador da Saga

> [!info] Onde chamar
> - **AWS:** sempre pelo API Gateway — `{{gatewayUrl}}{path}`. O gateway roteia
>   `/api/clients|vehicles|users` → Customer, `/api/budgets|payments` → Billing,
>   `/api/products|stocks` → Execution e o resto (`/order`, `/service-types`,
>   `/monitoring`) → OS Service.
> - **Local:** `docker compose -f workbench-messaging/docker-compose.dev.yml --profile app up -d --build`
>   e use o gateway local `http://localhost:8000` (mesmo roteamento) ou o serviço direto:
>   OS `:8080`, Customer `:8081`, Billing `:8082`, Execution `:8083`.
> - Todas as rotas abaixo exigem `Authorization: Bearer <jwt>` salvo indicação contrária.
>   Erros seguem `{"timestamp": "...", "status": 409, "error": "mensagem em português"}`.

| Método | Rota | Perfis | Resposta |
|---|---|---|---|
| POST | `/order` | ADMIN, TECHNICIAN | 201 OS `RECEBIDA` · 404 cliente/veículo · 422 tipo de serviço inexistente · 503 Customer fora |
| GET | `/order` | ADMIN, TECHNICIAN | 200 lista (ordenada por prioridade de status, depois mais antigas) |
| GET | `/order/id/{id}` | ADMIN, TECHNICIAN | 200 · 404 |
| GET | `/order/document/{cpfCnpj}` | staff ou o próprio cliente | 200 histórico do cliente · 403 outro documento |
| PATCH | `/order/{id}` | ADMIN, TECHNICIAN | 204 · 409 status da Saga / serviço pendente · 422 transição inválida |
| POST | `/order/{id}/diagnosis` | ADMIN, TECHNICIAN | 200 OS `EM_DIAGNOSTICO` — **dispara a Saga** · 409 Saga já em andamento |
| GET | `/order/{id}/saga` | ADMIN, TECHNICIAN | 200 passo da Saga e motivo da falha · 404 OS sem diagnóstico |
| POST | `/order/{id}/decision` | staff ou o próprio cliente | 204 · 403 · 409 OS fora de `AGUARDANDO_APROVACAO` |
| POST | `/order/{id}/payment-retry` | staff ou o próprio cliente | 202 nova cobrança pedida · 409 OS fora de `PAGAMENTO_PENDENTE` |
| GET | `/order/{id}/services` | ADMIN, TECHNICIAN | 200 serviços da OS → [[API - Servicos]] |
| PATCH | `/order/{id}/services/{serviceId}/status` | ADMIN, TECHNICIAN | 200 → [[API - Servicos]] |

## POST /order — Abrir OS

```json
{ "cpfCnpj": "52998224725", "placaVeiculo": "ABC-1234", "serviceTypes": ["TROCA_OLEO", "ALINHAMENTO"] }
```
**201**
```json
{ "id": "0c5e...", "serviceTypeName": "[TROCA_OLEO, ALINHAMENTO]", "serviceStatus": "RECEBIDA",
  "listService": ["TROCA_OLEO", "ALINHAMENTO"], "cpfCnpj": "52998224725", "placaVeiculo": "ABC1234",
  "rejectionReason": null, "createdAt": "...", "updatedAt": "..." }
```
Cada tipo de serviço vira um serviço da OS em `TO_DO`. `serviceTypeName` é um resumo
legado (texto, herdado do monólito); use `listService` ou `GET /order/{id}/services`.

## POST /order/{id}/diagnosis — Diagnóstico (inicia a Saga)

```json
{
  "parts":    [ { "productId": "665f...", "quantity": 2 } ],
  "services": [ { "serviceType": "TROCA_OLEO", "laborCost": 80.00, "laborHours": 1.0, "useDefault": false } ]
}
```
- `parts`: peças/insumos a reservar no Execution.
- `services`: mão de obra por serviço. Sem `laborCost`, `useDefault: true` usa o custo do
  catálogo (`/service-types`), senão fica 0 (ADR-0005).

Depois, de forma assíncrona: `ComandoReservarEstoque` → Execution → `ReservaConfirmada` →
`ComandoGerarOrcamento` → Billing → `OrcamentoGerado` → OS em **`AGUARDANDO_APROVACAO`**.

### Quando a Saga falha (ex.: falta de peça)

Com estoque insuficiente o Execution responde `ReservaFalhou`: nada é reservado, a Saga
vai para `FALHOU` e a OS continua em `EM_DIAGNOSTICO`. O motivo aparece em:

```http
GET /order/{id}/saga
```
```json
{ "step": "FALHOU", "completedSteps": ["INICIADA"],
  "failureReason": "Estoque disponível insuficiente para o produto 665f.... Disponível: 100, solicitado: 5000",
  "pendingCommand": null, "retryCount": 0, "updatedAt": "..." }
```
Para seguir, registre **um novo diagnóstico** (`POST /order/{id}/diagnosis`) com outras
quantidades/peças: a mesma Saga recomeça do início. Com a Saga em andamento, um segundo
diagnóstico é recusado (409) para não duplicar reserva nem orçamento.

## POST /order/{id}/decision — Aprovar/recusar orçamento

```json
{ "decision": "APPROVED" }
```
```json
{ "decision": "REJECTED", "reason": "Valor acima do esperado" }
```
- `APPROVED` → OS `APROVADO`, reserva confirmada (baixa de estoque).
- `REJECTED` → OS `RECUSADA`, reserva liberada (compensação da Saga).

## PATCH /order/{id} — Avanço manual de status

```json
{ "status": "EM_EXECUCAO" }
```
Fluxo: `RECEBIDA → EM_DIAGNOSTICO → AGUARDANDO_APROVACAO → APROVADO → EM_EXECUCAO →
FINALIZADA → PAGAMENTO_PENDENTE → PAGO → ENTREGUE` (ou `RECUSADA`).

- Transição fora da ordem → **422**.
- `AGUARDANDO_APROVACAO`, `APROVADO`, `RECUSADA`, `PAGO` e `ENTREGUE` são decididos pela Saga:
  numa OS com Saga, pedi-los aqui → **409** (use `/decision` ou aguarde o pagamento).
- `FINALIZADA` exige **todos os serviços `DONE`** → senão **409**. O caminho normal é
  executar os serviços (`/order/{id}/services/...`): o último `DONE` finaliza a OS sozinho.
- Ao entrar em `PAGAMENTO_PENDENTE` a Saga pede a cobrança ao Billing
  (`ComandoCobrarPagamento`); o link do Mercado Pago vai por e-mail (ao cliente com o canal SES; com o SNS, ao endereço inscrito no tópico).

## POST /order/{id}/payment-retry

Gera uma nova cobrança (referência `<OS>-N`) quando a anterior foi recusada ou expirou.
Sem corpo.

---

## Links Relacionados
- [[API - Servicos]]
- [[API - Orcamento]]
- [[API - Estoque]]
- [[Ciclo de Vida da OS]]
