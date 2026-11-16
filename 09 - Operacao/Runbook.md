---
title: Runbook
tags:
  - operacao
  - runbook
  - saga
aliases:
  - Runbook de Operação
---

# Runbook

O que fazer quando algo dá errado com a plataforma no ar. Cada caso diz como perceber,
como achar a causa e como resolver. Comandos `kubectl` e `aws` assumem o terminal já
apontado para o cluster e a conta certos (ver [[Deploy na AWS]]).

> [!tip] Seguir uma OS por todos os serviços
> No Datadog Logs, busque `@saga_id:<id>` ou `@service_order_id:<id da OS>`. Os 4 serviços
> gravam esses campos em JSON. Para o estado atual da Saga:
> `GET /order/{id}/saga` (staff) mostra o passo, os passos concluídos e o motivo da falha.

---

## 1. Alarme "DLQ não vazia"

**Como aparece:** e-mail do tópico `workbench-alerts` (alarme do CloudWatch
`<fila>-dlq-not-empty`, criado pelo `workbench-messaging`).

**O que significa:** um serviço tentou processar a mesma mensagem 3 vezes
(`max_receive_count`) e desistiu. A OS correspondente está parada nesse passo.

| DLQ | Quem não conseguiu processar | Mensagens típicas |
|---|---|---|
| `workbench-os-saga-replies-queue-dlq` | os-service (orquestrador) | `ReservaConfirmada`, `OrcamentoGerado`, `PagamentoConfirmado`… |
| `workbench-billing-commands-queue-dlq` | billing-service | `ComandoGerarOrcamento`, `ComandoCobrarPagamento` |
| `workbench-execution-commands-queue-dlq` | execution-service | `ComandoReservarEstoque`, `ComandoConfirmarReserva`, `ComandoLiberarReserva` |

**Passos:**
1. **Ache a causa no log** do serviço dono da fila: os consumidores registram
   `Failed to process ...; leaving for redrive/DLQ. sqsMessageId=<id>` com a exceção. (O
   corpo da mensagem não vai para o log, porque leva CPF/CNPJ.)
2. **Corrija a causa** (deploy de correção, banco fora, segredo errado…). Reprocessar sem
   corrigir só manda a mensagem de volta para a DLQ.
3. **Devolva as mensagens à fila de origem:**
   ```bash
   DLQ_ARN=$(aws sqs get-queue-attributes --queue-url <url-da-dlq> \
     --attribute-names QueueArn --query Attributes.QueueArn --output text)
   aws sqs start-message-move-task --source-arn "$DLQ_ARN"
   ```
   Os participantes são idempotentes, então reprocessar uma mensagem que já teve efeito
   não duplica nada.
4. **Confira a OS:** `GET /order/{id}/saga` deve sair do passo em que estava.

---

## 2. OS parada

**Como aparece:** cliente reclama, ou a OS fica muito tempo no mesmo status.
Veja `GET /order/{id}/saga`:

| Passo da Saga | Causa provável | O que fazer |
|---|---|---|
| `FALHOU` com motivo de estoque | Peça sem estoque na reserva | Ajustar estoque (`/api/stocks`) e refazer o diagnóstico: `POST /order/{id}/diagnosis` |
| `FALHOU` com `timeout em ComandoReservarEstoque` / `ComandoGerarOrcamento` | Execution ou billing fora do ar; a reserva foi liberada | Confirmar que o serviço voltou e refazer o diagnóstico |
| `AGUARDANDO_PAGAMENTO` com motivo | Pagamento recusado ou cobrança sem resposta | Nova cobrança: `POST /order/{id}/payment-retry` (cliente dono ou staff) |
| `AGUARDANDO_APROVACAO` | Cliente ainda não decidiu | Nada a fazer no sistema; a reserva continua presa (não há prazo automático) |
| `COMPENSANDO` por muito tempo | `ComandoLiberarReserva` sem resposta | Ver a DLQ do execution (seção 1) |
| Qualquer passo com comando pendente antigo | Mensagem na DLQ | Seção 1 |

Status da Saga (`APROVADO`, `PAGO`, `ENTREGUE`…) **não** devem ser forçados pelo
`PATCH /order/{id}/status`: a API recusa (409), porque isso pularia a baixa de estoque
ou o pagamento.

---

## 3. Trocar as chaves do JWT

Tokens RS256: a Lambda assina com `JWT_PRIVATE_KEY` e todos verificam com `JWT_PUBLIC_KEY`
(o token de serviço do os-service usa o outro par, `JWT_SERVICE_*`).

1. Gere um par novo (comando em [[JWT#Formato das chaves]]) e atualize **os dois** secrets do
   par na org (privada e pública).
2. Rode de novo o CD do `workbench-lambda` e o pipeline dos serviços que usam o par (para o
   par principal: os 4; para o de serviço: os-service e customer).
3. Até tudo terminar, um lado pode recusar token do outro. Depois, todo token antigo deixa
   de valer: clientes e equipe fazem login de novo. Se só a chave **privada** vazou, troque
   o par inteiro — a pública sozinha não emite token.

---

## 4. Reverter um deploy

```bash
kubectl rollout undo deployment/<serviço> -n <serviço>
kubectl rollout status deployment/<serviço> -n <serviço>
```

> [!warning] Migrations
> O Flyway só anda para frente. Se a versão nova trouxe migration, a versão anterior roda
> sobre o schema novo: confira se ela continua compatível antes de reverter.

---

## 5. Serviço não sobe

| Sintoma no log | Causa | Correção |
|---|---|---|
| `Could not resolve placeholder 'JWT_PUBLIC_KEY'` (ou `JWT_SERVICE_*`, `SPRING_DATASOURCE_PASSWORD`, `PAYMENT_PROVIDER`) | Variável obrigatória faltando (não há valor padrão) | Conferir o secret da org e o Secret do pod |
| `Admin admin@workbench.dev ainda usa a senha padrão` (customer) | Admin ainda em `admin123` sem `ADMIN_INITIAL_PASSWORD` | Criar o secret `ADMIN_INITIAL_PASSWORD` (≥ 8 caracteres) e rodar o pipeline |
| Pod em `CrashLoopBackOff` sem log da aplicação | Falta de memória ou probe | `kubectl describe pod` (eventos) e `kubectl logs --previous` |

---

## Notas relacionadas

- [[Deploy na AWS]] e [[Desligar a AWS]]
- [[Arquitetura e Saga - Visao Completa V2]] — o fluxo da Saga passo a passo
- [[Contratos de Mensagem]] — formato de cada mensagem
