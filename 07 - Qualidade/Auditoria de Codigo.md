---
title: Auditoria de Código
tags:
  - qualidade
  - auditoria
aliases:
  - AUDITORIA-MICROSSERVICOS
---

# Auditoria de código — microsserviços Workbench

> Feita com o skill `ponytail-audit` (repositório `ponytail`), mais um olhar de clean
> code e padrões de projeto. **4ª rodada (14/11/2026)**; a 3ª foi em 11/11/2026, depois
> das correções da 1ª e da 2ª e da migração para uma classe por caso de uso.
> Branches: `ci/sonarcloud-config` dos 4 serviços — **a maior parte das mudanças ainda
> não está commitada** (ver achado 1 da 4ª rodada).
> `mvn verify` nos 4 (15/11/2026, depois da revisão externa): **492 testes, 0 falhas**
> (os 255, billing 85, customer 81, execution 71); cobertura de linhas: os 91,1%, billing 87,2%,
> customer 87,0%, execution 89,0% (gate JaCoCo de 80% atingido em todos).

**O que estes repositórios fazem:** quatro microsserviços Java/Spring Boot de uma
oficina mecânica. O **os-service** cria a ordem de serviço (OS) e orquestra uma
**Saga** (sequência de passos entre serviços, trocando mensagens por SNS/SQS); o
**execution-service** reserva peças no estoque (MongoDB); o **billing-service** gera
o orçamento e cobra pelo Mercado Pago; o **customer-service** guarda clientes,
veículos e usuários da equipe.

**Carga assumida:** baixa (projeto acadêmico), mas com **2 ou mais réplicas por
serviço** (HPA) e mensagens que podem chegar **mais de uma vez** (SQS entrega "pelo
menos uma vez").

---

## 1. Situação dos achados da 1ª rodada

| # | Achado | Situação | O que foi feito |
|---|---|---|---|
| 1 | Qualquer pessoa marcava pagamento como pago | ✅ Corrigido | Webhook simulado só existe com `payment.provider=fake` (local). Na AWS, `PaymentStatusPollingJob` (ShedLock) consulta `GET /v1/payments/search?external_reference={OS}`. Teste garante 404 do webhook com `mercadopago`. |
| 2 | Cliente via dados de outros clientes | ✅ Corrigido | `Requester` (subject do JWT + se é cliente) nos casos de uso dos 3 serviços. os: `/order/document/{cpf}`; billing: orçamento/pagamento/histórico (dono = `customerDocument` do orçamento, enviado pelo os-service, migration `V7`); customer: cliente por id/documento e veículos. `GET /api/clients` (lista) só staff. 403 via `SecurityException`. |
| 3 | Cliente não conseguia decidir o orçamento | ✅ Corrigido | `POST /order/*/decision` liberado para `CLIENT`; o dono é conferido no `DecideOrderUseCase`. |
| 4 | Estoque reservado 2× para a mesma OS | ✅ Corrigido | `reserve()` devolve a reserva ACTIVE existente; `confirm()`/`release()` repetidos devolvem o resultado anterior. |
| 5 | `@Transactional` sem efeito no execution | ✅ Corrigido | Bean `MongoTransactionManager`. Escritas de estoque também transacionais; o MongoDB aborta a 2ª gravação concorrente (WriteConflict). O handler só transforma erro **de negócio** em `ReservaFalhou`; erro técnico volta para a fila (nova tentativa). `@Version` foi descartado: quebraria os documentos já gravados no Atlas. |
| 6 | Orquestrador aceitava eventos repetidos/fora de ordem | ✅ Corrigido | Cada evento só é aceito no passo esperado (`EXPECTED_STEP`); fora dele, log e descarte. |
| 7 | Cobrança duplicada no Mercado Pago | ✅ Corrigido | `createPayment()` devolve o pagamento existente sem chamar o gateway. |
| 8 | Comandos/e-mails saindo antes do commit | ✅ Corrigido (os) | `AfterCommit` no os-service: comandos da Saga e notificações saem depois do commit; falha é logada e o job de timeout reenvia. No billing o evento de pagamento **continua dentro da transação, de propósito**: se o SNS falhar, a decisão é desfeita e o job tenta de novo; o duplicado é descartado pelo item 6. |
| 9 | PATCH de status pulava a Saga | ✅ Corrigido | Status da Saga (`AGUARDANDO_APROVACAO`, `APROVADO`, `RECUSADA`, `PAGO`, `ENTREGUE`) bloqueados no PATCH **só quando a OS tem Saga** (409). Sem Saga, o modo manual do BDD segue funcionando. |
| 10 | CPF salvo com máscara, buscado sem | ✅ Corrigido | `ServiceOrder.normalizeDocument` ao criar, buscar e comparar com o token. |
| 11 | Nomes de mensagem como texto solto | ✅ Corrigido | `SagaMessages` nos 3 serviços da Saga **+ testes de contrato**: fonte única `workbench-messaging/contracts/saga-messages.json` (emissor, consumidor, campos obrigatórios, exemplo), cópia em cada serviço sincronizada por `scripts/sync-saga-contract.sh` (`--check` confere). `OsSagaContractTest`, `BillingSagaContractTest` e `ExecutionSagaContractTest` conferem nomes, campos do que cada um publica e se aceita o exemplo que consome. Validado com mutação: renomear um campo no contrato derruba o teste. |
| 12 | Teste mockava método que o controller não chama | ✅ Corrigido | Sobrecarga de 3 argumentos removida; testes usam a assinatura real. |
| 13 | "Recusado" repetido devolvia erro | ✅ Corrigido | Recusa repetida é ignorada (idempotente). |
| 14 | Senha padrão `admin123` + validação pública | ⏸️ Não corrigido | Precisa de infra (deixar `/api/users/auth/validate` só dentro do cluster) e de troca de senha pós-deploy. Mudar a migration `V2` já aplicada quebraria o Flyway. |
| 15 | Busca de OS por id → 422 | ✅ Corrigido | `NoSuchElementException` → 404. (Tipo de serviço inexistente na criação **continua 422**, de propósito: é dado inválido no corpo, não rota inexistente.) |
| 16 | Regra de mão de obra copiada | ✅ Corrigido | `WorkshopService.resolveLabor`, usada pelos dois casos de uso. |
| 17 | Payload malformado no billing ia para a DLQ | ✅ Corrigido | Leitura dentro do `try` → `OrcamentoFalhou`. |
| 18 | Controller do billing falava com o repositório | ✅ Corrigido | Consultas via `PaymentUseCases`. |

Também corrigido de passagem: rota inexistente no billing respondia **500** (agora 404);
nomes de classe totalmente qualificados no meio do código do os-service/customer
viraram `import`; `Stock` perdeu o `@Setter` (mínimo muda por `changeMinimum`).

---

## 2. Achados da 2ª rodada — situação

| # | Achado | Situação | O que foi feito |
|---|---|---|---|
| 1 | Cobrança recusada não podia ser refeita | ✅ Corrigido | **os:** pagamento recusado deixou de ser "compensação" — a Saga fica em AGUARDANDO_PAGAMENTO com o motivo, e `POST /order/{id}/payment-retry` (cliente dono ou staff, `RetryPaymentUseCase`) comanda nova cobrança. **billing:** `CreatePaymentUseCase` reabre o pagamento RECUSADO com novo link; cada tentativa tem referência própria no Mercado Pago (`<OS>`, `<OS>-2`…, coluna `attempt`, migration `V8`) para a consulta não confundir a nova tentativa com a cancelada. |
| 2 | Estorno não devolvia o dinheiro | ✅ Corrigido | O job grava o id do pagamento aprovado (`gateway_transaction_id`, `V8`); `RefundPaymentUseCase` chama `POST /v1/payments/{id}/refunds` com `X-Idempotency-Key` (estorno repetido não devolve 2×). Aprovado pelo webhook simulado (fake) não tem transação e não chama o gateway. |
| 3 | Senha padrão do admin + login sem limite | ✅ Corrigido (parcial por infra) | `ADMIN_INITIAL_PASSWORD` (secret da org, injetado pela pipeline) substitui `admin123` no start — só enquanto o admin ainda usa a padrão, nunca sobrescreve senha trocada; sem ela, aviso no log. `LoginAttemptLimiter`: 5 erros seguidos bloqueiam o e-mail por 15 min, mesma resposta de credencial inválida. *Fica para infra:* deixar `/api/users/auth/validate` acessível só de dentro do cluster. |
| 4 | Segurança/helpers copiados em 3–4 serviços | ⏸️ Decisão: manter | Independência de deploy dos microsserviços vale mais que a cópia hoje. Revisitar (lib `workbench-commons` só com `Requester`/JWT) se surgir 5º serviço ou outra correção de segurança transversal. |
| 5 | Dedupe em memória quase redundante | ⏸️ Decisão: manter | Não protege entre pods (quem protege é a proteção de passo e a idempotência dos participantes), mas evita log repetido no mesmo pod. Custo zero. |
| 6 | Mensagem interna no corpo do 409 | ✅ Corrigido | Falha de comunicação com o Customer Service (erro HTTP **ou** fora do ar/timeout, que antes virava 422) agora é `CustomerServiceUnavailableException` → **503** com mensagem genérica; o detalhe vai só para o log. |
| 7 | `findLowStock` lê o estoque todo | ⏸️ Decisão: manter | Não dá para virar query: os `BigDecimal` são gravados como **texto** no MongoDB, e `$lte` entre textos compara letra a letra (`"10" < "9"`). Corrigir exige migrar o formato (Decimal128) — só se o catálogo crescer. |

## 3ª rodada do `ponytail-audit` — código depois destas correções

**Achado e já corrigido nesta rodada:**

- **O limite de login podia esgotar a memória** (`workbench-customer-service/.../LoginAttemptLimiter.java`) — guardava uma entrada por e-mail errado e só removia no acerto; milhares de e-mails inventados faziam o mapa crescer sem fim. Agora há teto (`MAX_TRACKED`) que descarta contagens parciais e preserva os bloqueios em vigor (teste cobre).
- **Log de "pagamento conciliado" nunca aparecia** (`PaymentStatusPollingJob`) — comparava o status depois do objeto já ter sido alterado.

**Abertos (bom ter):**

1. **Limite de login é por réplica** — com N pods, o atacante tem N×5 tentativas por janela. Marcado no código com `shortcut:`; trocar por contador compartilhado (tabela/Redis) se o serviço ficar exposto à internet.
2. **Cópias do contrato da Saga não são conferidas no CI** — *atualizado na 4ª rodada:* o job `unit-test` dos 3 serviços da Saga agora baixa o contrato da `main` do `workbench-messaging` e compara. Mas o contrato ainda não está na `main` (achado 5 da 4ª rodada), então o passo só avisa e segue.
3. **Estorno sem fluxo que o dispare** — o `ComandoEstornarPagamento` está implementado no billing, mas o orquestrador ainda não envia (é `optionalFor` no contrato). Só importa se a regra de negócio passar a estornar.

Nenhum achado "corrigir já" nesta rodada.

`Lean:` −1 método morto (`findMovements`, só usado pelo próprio teste); buscas "ou 404" e registro de movimento de estoque deixaram de ser repetidos em cada caso de uso (métodos `default` nas portas: `getById`, `getByProductId`, `record`).


## 4ª rodada do `ponytail-audit` (14/11/2026)

**O que foi lido:** a Saga ponta a ponta (`SagaOrchestrator`, `SagaState`, timeout,
consumidores SQS dos 3 serviços), cobrança e conciliação do billing (`CreatePaymentUseCase`,
`PaymentDecisionRecorder`, `MercadoPagoGatewayAdapter`, `PaymentStatusPollingJob`),
reserva, baixa e liberação de estoque no execution, os casos de uso de OS que mexem na
Saga (`DiagnoseOrderUseCase`, `DecideOrderUseCase`, `UpdateOrderUseCase`), as pipelines e
o estado dos repositórios no GitHub. Mesma carga assumida: baixa, mas com 2+ réplicas e
mensagens que chegam mais de uma vez.

### Corrigir já

1. **Quase todo o trabalho das revisões só existe nesta máquina** (os 4 serviços, `workbench-messaging`, `workbench-gateway`, `workbench-lambda`, `workbench-monolith`, `workbench-technical-documentation`)
   - **O que é:** as correções das 3 rodadas, a troca para uma classe por caso de uso, o Spring Boot 4.0.9, o contrato da Saga, o compose completo, as rotas do gateway por serviço e a ADR renumerada.
   - **Problema:** está tudo como mudança não commitada (por volta de 250 arquivos só nos 4 serviços). No GitHub, a branch dos serviços ainda tem o Spring Boot **4.0.5**, com os CVEs críticos. O execution de lá ainda lê a chave antiga do Mongo e, na AWS, tentaria conectar em `localhost`.
   - **Correção:** commitar e dar push por repositório, nas branches dos PRs já abertos, e deixar o CI rodar.
   - **Se não fizermos:** quem avaliar pelo GitHub vê o código antigo, e um deploy a partir do GitHub sobe o execution sem banco. Um disco com problema apaga semanas de trabalho.

2. ✅ **Corrigido em 14/11** — **OS só com mão de obra trava depois da aprovação** (`workbench-execution-service/.../ReservationTransition.java`)
   - **O que é:** na aprovação, o os-service manda `ComandoConfirmarReserva`; o execution baixa as reservas da OS.
   - **Problema:** o diagnóstico aceita uma OS sem peças (ex.: alinhamento). Ela não tem reserva, e `apply` lança `NoSuchElementException`. O handler não trata o erro, então a mensagem volta para a fila até cair na DLQ. A Saga esgota os reenvios e vai para `FALHOU`. Quando a OS chega a `PAGAMENTO_PENDENTE`, a cobrança é pedida, mas o `CobrancaCriada` e o `PagamentoConfirmado` são descartados, porque a Saga não está mais em `AGUARDANDO_PAGAMENTO`. O cliente não recebe o link e a OS nunca vira `PAGO`. A recusa do orçamento tem o mesmo problema ao liberar a reserva.
   - **Correção:** se a OS não tem reserva nenhuma, devolver lista vazia em vez de lançar erro: não há nada para baixar ou liberar. Trocar o teste `confirmThrowsWhenNoActiveReservations` por um que espera lista vazia.
   - **Se não fizermos:** todo serviço sem peça fica preso sem saída pela API, e o PATCH manual de `PAGO`/`ENTREGUE` é bloqueado porque a OS tem Saga.

3. ✅ **Corrigido em 14/11** — **Timeout na cobrança ou na baixa deixa a OS presa para sempre** (`workbench-os-service/.../SagaOrchestrator.java`, `compensateOnTimeout`)
   - **O que é:** quando um comando fica sem resposta por 3 reenvios, o orquestrador compensa (reserva/orçamento) ou marca a Saga como `FALHOU` (resto).
   - **Problema:** se o billing ficar fora por uns minutos depois de `ComandoCobrarPagamento`, a Saga vai para `FALHOU`. A nova cobrança (`POST /order/{id}/payment-retry`) exige `AGUARDANDO_PAGAMENTO` e responde 409. Se o billing voltar e o cliente pagar, o `PagamentoConfirmado` é descartado pelo mesmo motivo. Resultado: cliente pagou e a OS fica em `PAGAMENTO_PENDENTE`.
   - **Correção:** para `ComandoCobrarPagamento` e `ComandoConfirmarReserva`, registrar o motivo (`recordFailure`) e limpar a pendência, ficando em `AGUARDANDO_PAGAMENTO`. Assim a nova cobrança funciona e o evento atrasado é aceito. Um teste para cada um dos dois comandos.
   - **Se não fizermos:** uma indisponibilidade curta do billing exige editar o banco à mão para destravar a OS.

### Deveria corrigir

4. ✅ **Corrigido em 14/11** — **Saga que falha continua sendo reprocessada a cada 30 s** (`workbench-os-service/.../SagaState.java`, `markFailed`)
   - **O que é:** o job de timeout busca toda Saga com comando pendente e sem resposta.
   - **Problema:** `markFailed` não limpa o comando pendente. Depois de falhar (ex.: `ComandoLiberarReserva` sem resposta), a Saga volta na busca a cada janela, gera um `warn` e grava de novo no banco, para sempre.
   - **Correção:** chamar `clearPendingCommand()` dentro de `markFailed`. Uma linha.
   - **Se não fizermos:** log poluído e escrita inútil no banco por OS travada; o alerta de verdade some no meio.

5. **A conferência do contrato no CI está desligada na prática** (`.github/workflows/pipeline.yml` de os, billing e execution)
   - **O que é:** o job `unit-test` baixa `contracts/saga-messages.json` da `main` do `workbench-messaging` e compara com a cópia local.
   - **Problema:** esse arquivo só existe localmente (`contracts/` não commitado no messaging). O download falha, o passo emite um aviso e sai com sucesso.
   - **Correção:** commitar o `contracts/` no PR do `workbench-messaging` e mergear na `main`. Nada muda nas pipelines.
   - **Se não fizermos:** o contrato pode divergir entre os serviços sem nenhum CI acusar.

6. **Chamadas HTTP sem timeout** (`workbench-billing-service/.../MercadoPagoGatewayAdapter.java`; `workbench-os-service/.../CustomerRest*Adapter.java`)
   - **O que é:** o billing consulta o Mercado Pago a cada 30 s; o os-service chama o customer-service ao criar a OS e ao enviar e-mail.
   - **Problema:** nenhum `RestClient` tem timeout de conexão ou de leitura. Se o Mercado Pago aceitar a conexão e não responder, o job de consulta fica parado nessa chamada e nenhum pagamento é confirmado até o pod reiniciar. Passados os 2 min do ShedLock, outro pod entra e pode parar do mesmo jeito.
   - **Correção:** definir timeout de conexão e de leitura (ex.: 5 s e 10 s) nas propriedades de cliente HTTP do Boot, e fazer o adapter do Mercado Pago usar o `RestClient.Builder` injetado em vez de `RestClient.builder()`.
   - **Se não fizermos:** uma lentidão do Mercado Pago congela a confirmação de todos os pagamentos.

**O que foi feito nos achados 2–4 (14/11/2026, não commitado):**
- **execution — `ReservationTransition`:** OS sem reserva devolve lista vazia na baixa e na liberação. O teste que esperava erro virou `confirmAndReleaseReturnEmptyWhenOrderHasNoReservation`.
- **os — `SagaOrchestrator.compensateOnTimeout`:** um timeout esgotado em `ComandoConfirmarReserva` ou `ComandoCobrarPagamento` registra o motivo, limpa a pendência e mantém a Saga em `AGUARDANDO_PAGAMENTO`. A nova cobrança e a confirmação atrasada passam a ser aceitas.
- **os — `SagaState.markFailed`:** limpa o comando pendente; o job de timeout não reprocessa mais a Saga encerrada.
- **os — `onReservationConfirmed`:** um `ReservaBaixada` atrasado não apaga mais uma cobrança pendente. Achado no caminho, mesmo risco do achado 3.
- 4 testes novos em `SagaOrchestratorTest`, um por caso.

**Continuam abertos, como decisão registrada:** limite de login por réplica (`shortcut:` no
código) e estorno sem fluxo que o dispare (`optionalFor` no contrato).

**Veredito:** com 2, 3 e 4 corrigidos, falta o achado 1 (commitar e dar push), que segue
sendo o mais urgente; depois o 5 e o 6.

**Não verificado:** não rodei a Saga ponta a ponta nesta rodada (só os testes); não li
linha a linha os controllers de CRUD nem a Lambda; não conferi o Terraform.

## Revisão da Saga (15/11/2026)

Revisão focada na Saga, depois das correções da 4ª rodada. Dois pontos corrigidos, um registrado:

| # | Achado | Situação | O que foi feito |
|---|---|---|---|
| 1 | Aprovação e recusa simultâneas deixavam estoque e OS divergentes | ✅ Corrigido | Nenhuma entidade tinha trava otimista, e as duas decisões gravavam, enviando baixa **e** liberação da reserva. Agora `saga_state` tem `version` (`@Version`, migration `V9`): a segunda transação falha e a API responde **409**, sem enviar comando, porque os comandos só saem depois do commit. No execution, baixar uma reserva já liberada (ou o contrário) volta a ser erro; a lista vazia ficou só para a OS sem reserva. Testes: `SagaStateConcurrencyIntegrationTest` (Postgres real) e `confirmAfterReleaseIsAConflict`. |
| 2 | Reserva de estoque sem prazo | ⏸️ Registrado | OS que fica em `AGUARDANDO_APROVACAO` prende as peças para sempre. Precisa de regra de negócio (prazo para recusar automaticamente). |
| 3 | Evento de uma rodada anterior derrubava a Saga nova | ✅ Corrigido | O `sagaId` era o id da OS em todas as rodadas. Agora cada início ou novo diagnóstico gera um `sagaId` novo (coluna `saga_id`, migration `V9`, com as linhas antigas preenchidas com o id da OS para não perder respostas em trânsito). O orquestrador descarta resposta com `sagaId` de outra rodada. Teste: `replyFromThePreviousRunIsIgnoredAfterANewDiagnosis`. |

## Revisão externa (15/11/2026)

Uma revisão externa listou 9 pontos. Todos foram conferidos no código; os que procediam foram corrigidos:

| # | Ponto | Situação | O que foi feito |
|---|---|---|---|
| 1 | `JWT_SECRET` e senha do banco com valor padrão no `application.yml` | ✅ Corrigido | Sem padrão nos 4 serviços: sem a variável, o serviço não sobe (`Could not resolve placeholder 'JWT_SECRET'`, conferido). Os valores de dev foram para `application-local.yml`, que o compose ativa (`SPRING_PROFILES_ACTIVE=local`); os testes têm o seu `application.properties`. |
| 2 | Billing com `fake` como provider padrão (webhook aberto) | ✅ Corrigido | `PAYMENT_PROVIDER` sem padrão e sem `matchIfMissing`: sem ele o serviço não sobe. `fake` só no perfil local e nos testes. |
| 3 | Uma thread para todos os `@Scheduled`; Mercado Pago sem timeout | ✅ Corrigido | `spring.task.scheduling.pool.size` = 4 em os, billing e execution. Timeouts no Mercado Pago (5 s / 10 s) e no customer-service (2 s / 5 s), configuráveis. |
| 4 | `SagaOrchestrator`: `orElseThrow()` sem mensagem; reenvio em uma transação só | ✅ Corrigido | Mensagem nos 3 `orElseThrow`. O job de timeout chama `resendTimedOut(osId, limite)` uma vez por OS, cada uma na sua transação; uma falha não desfaz as outras (e a Saga que recebeu a resposta no meio do caminho não é reenviada). |
| 4 | Dividir o orquestrador; payloads tipados | ⏸️ Decisão: manter | O orquestrador é uma máquina de estados só; dividir espalha a regra. Os payloads são o contrato entre repositórios, já conferido pelos testes de contrato. |
| 5 | Campo ausente virava o texto `"null"` no orçamento | ✅ Corrigido | Campos obrigatórios das peças e da mão de obra são validados (ausente → `OrcamentoFalhou` com o nome do campo); `sku`/`brand` ausentes ficam nulos. |
| 6 | Corpo da mensagem (com CPF/CNPJ) no log de erro | ✅ Corrigido | Os 3 consumidores logam só o id da mensagem do SQS. |
| 6 | Idempotência só no webhook | ❌ Não procede | Está em todos os participantes (reserva, baixa/liberação, orçamento, cobrança, decisão de pagamento) e no orquestrador; o dedupe em memória é só um extra. |
| 7 | Admin sobe com `admin123` sem `ADMIN_INITIAL_PASSWORD` | ✅ Corrigido | Fora do perfil local o customer-service não sobe com o admin na senha padrão e sem senha válida; a pipeline passou a exigir o secret. |
| 7 | Bloqueio de login por e-mail permite travar um usuário | ⏸️ Decisão: manter | O login chega pela Lambda, então o IP visto pelo serviço não é o do cliente; bloquear por IP não funcionaria. O bloqueio dura 15 min. |
| 8 | Código de segurança copiado entre serviços | ⏸️ Decisão: manter | Mesma decisão da 2ª rodada (item 4): independência de deploy. |
| 9 | Detalhes do `JwtService` e imports com `*` | ✅ Corrigido | `isExpired` removido (o parser já valida), `catch (JwtException \| IllegalArgumentException)`, sem `@SuppressWarnings`; imports explícitos nos 10 controllers. |

## Revisão externa — achados novos (15/11/2026)

| # | Achado | Situação | O que foi feito |
|---|---|---|---|
| 1 | Postgres de dev (senha `password`, sem volume) ia junto no deploy de billing e customer | ✅ Corrigido | Saiu do `app.yaml` para `k8s/postgres-local.yaml` (o pipeline não aplica); o pipeline apaga o que sobrou de deploys antigos. |
| 2 | Os 4 Services eram LoadBalancer público (dava para pular o authorizer) | ✅ Corrigido | NLB interno nos 4 (`aws-load-balancer-internal`). O gateway passou a usar um VPC Link por serviço e acha cada NLB pela tag `kubernetes.io/service-name` (sem secrets de origem). O pipeline recria uma vez o Service que ainda for público. `terraform validate` ok; **não aplicado na AWS**. |
| 3 | Lambda mandava e-mail/senha do staff por URL sem exigência de HTTPS | ✅ Corrigido | `precondition` no Terraform da Lambda de staff: só `https://` ou o NLB interno com `customer_service_url_internal = true` (o CD define). |
| 4 | Pods sem hardening; JVM com 25% da RAM | ✅ Corrigido | `securityContext` no container (não-root, sem escalar privilégio, sem capabilities, rootfs somente leitura com `/tmp` em `emptyDir`, seccomp), `startupProbe`, PDB (`maxUnavailable: 1`), NetworkPolicy só na 8080 e `-XX:MaxRAMPercentage=75.0`. Os Dockerfiles já usavam usuário não-root; agora com UID numérico (10001), que o `runAsNonRoot` consegue conferir. Testado no Docker local: sobe com `--read-only`, sem capabilities, como UID 10001. |
| 5 | `:latest` publicado e `java-lib.version: "latest"` | ✅ Corrigido | Sem tag `:latest`; `dd-java-agent` fixo em `v1.68.2` (versão conferida no registry). |
| 6 | Lambda revelava quais CPFs existem (404/403/200); e-mail do staff em claro no log | ✅ Corrigido | CPF inexistente ou inativo recebe o mesmo **401** (o motivo vai só para o log, com CPF mascarado); e-mail do staff mascarado no log (`m***@dominio`). |
| 7 | Pipeline do customer exigia `ADMIN_INITIAL_PASSWORD` em todo deploy | ✅ Corrigido | Saiu da validação da pipeline; quem barra a senha padrão é o próprio serviço, que não sobe com ela. |
| 8 | Corrida em `CreatePaymentUseCase` criava preferência extra no Mercado Pago | ✅ Corrigido | A linha do orçamento é travada (`SELECT ... FOR UPDATE`) antes de ler o pagamento: a segunda réplica espera e devolve a cobrança da primeira. `ConcurrentChargeIntegrationTest` (Postgres real) falha sem a trava e passa com ela. |
| — | (achado na conferência) `app.yaml` com `image: REPLACE_IMAGE` gerava um rollout quebrado a cada deploy | ✅ Corrigido | O pipeline substitui a imagem antes do `apply` e não usa mais `kubectl set image`. O `Deployment` também deixou de fixar `replicas: 1`, que desfazia o HPA a cada deploy. |

## Correção de 15/11/2026 — pagamento descartado pela Saga

Achado ao rodar o roteiro do vídeo no compose local: a OS ficava em `PAGAMENTO_PENDENTE`.
O billing publicava `PagamentoConfirmado` com o id da OS como `sagaId`, e desde o `sagaId`
por rodada (ADR-0008) o orquestrador descartava o evento como "de outra rodada". Os testes
não pegaram porque as Sagas de teste usavam o id da OS como rodada.

| O que mudou | Onde |
|---|---|
| A cobrança guarda o `sagaId` do `ComandoCobrarPagamento` (também na nova cobrança após recusa) | billing: `Payment.bindToSaga`, `CreatePaymentUseCase`, migration `V9__payment_saga_id.sql` |
| O resultado do pagamento sai com esse `sagaId` (sem ele, o id da OS) | billing: `PaymentDecisionRecorder`, `SnsPaymentEventAdapter` |
| Teste do caminho real: Saga nova até `ENTREGUE`, e o pagamento com o id da OS é descartado | os: `newSagaRunsToDeliveredWhenEveryReplyCarriesItsRun` |
| Testes da cobrança com rodada, nova cobrança e fallback | billing: `PaymentUseCasesTest`, `SagaCommandHandlerTest` |

---

## 3. Clean code e padrões — records, `.builder()` e controllers

**Records (51 no total).** A maioria está certa: DTOs de entrada/saída, comandos e
respostas imutáveis — é o uso idiomático em Java 21. O problema não era a quantidade,
era **o mesmo conceito em 3 records** com conversões em cadeia: "peça a reservar"
existia como `DiagnoseOrderRequest.PartItem` → `DiagnoseOrderUseCase.PartItem` →
`SagaOrchestrator.ReserveItem`. Ficou só o DTO da web e o `ReserveItem`, com a
conversão no próprio request (`reserveItems()`, `labor()`). Regra prática: **um record
por fronteira** (HTTP, caso de uso, mensagem), nunca dois para a mesma fronteira.

**Onde ficam os DTOs (padronizado).** Nenhum controller declara record. Convenção
única, a que customer e execution já usavam: **um arquivo `<Recurso>Dtos` por
recurso** no pacote do controller (`BudgetDtos`, `PaymentDtos`, `FakePaymentWebhookDtos`,
`UserDtos`, `ProductDtos`, `ServiceTypeDtos`, `MonitoringDtos`, além de `ClientDtos`,
`VehicleDtos`, `StockDtos`). No os-service, os DTOs de OS já eram arquivos próprios
(`CreateOrderRequest`, `ServiceOrderResponse`…) e ficaram assim. Records de **entrada
de caso de uso** (`ReserveItem`, `PartInput`, `ServiceLabor`) continuam aninhados no
caso de uso: são o "contrato" dele, não DTO de HTTP.

**Idioma (decidido): código em inglês, mensagem ao cliente em português.**
- Identificadores traduzidos: handlers da Saga (`onStockReserved`, `onBudgetGenerated`,
  `onPaymentConfirmed`…), constantes (`SagaMessages.RESERVE_STOCK`…), `generateBudget`,
  `reserveStock`, campo `licensePlate` no domínio, nomes de métodos de teste.
- Mensagens que chegam ao cliente (corpo do erro HTTP e motivo da Saga) traduzidas e
  com acentuação: CPF/CNPJ, placa, veículo, estoque, pagamento, transições de status.
- **Ficaram em português de propósito, por serem dados e não código:** valores dos
  status (`RECEBIDA`, `PENDENTE`… — gravados no banco e expostos na API), passos da Saga
  gravados (`AGUARDANDO_RESERVA`…), nomes trafegados das mensagens
  (`"ComandoReservarEstoque"` — contrato entre repositórios), campos JSON da API
  (`placaVeiculo`, `cpfCnpj`) e a coluna `placa`. Mudá-los quebraria dados gravados,
  clientes da API e o contrato. Logs e comentários seguem em português.

**`.builder()` (40 chamadas).** ~80% são de bibliotecas (AWS SDK `PublishRequest`/
`ReceiveMessageRequest`, JJWT, `RestClient`) — isso é a API delas, não tem o que mudar.
O que incomodava era `@Builder` + `@Setter` no **domínio**: qualquer classe podia
montar um `Stock` sem passar pelas regras (`reserve`, `confirmReservation`). O `Stock`
perdeu o `@Setter`; os próprios testes usavam `setReservedQuantity` e passaram a usar
`reserve(...)`. Depois, **`Budget`** e **`StockReservation`** também perderam o
`@Setter`: o `Budget` nasce por `Budget.forServiceOrder(...)`, volta do banco por
`Budget.reconstitute(...)` e só muda por `revise(documento, itens)`, que recalcula os
totais (não dá mais para gravar um total que não bate com os itens). A
`StockReservation` nasce por `activate(...)` e só muda por `confirm()`/`release()`, que
exigem ACTIVE. Ainda têm `@Setter` (sem regra relevante): `BudgetItem`,
`PaymentHistory`, `WorkshopService`, `ServiceType`, `StockMovement`, `Product`.

**Controllers.** Estavam com responsabilidade demais em três pontos, todos corrigidos:
- `ServiceOrderController.decide` extraía papéis do token e decidia regra de acesso →
  agora monta um `Requester` e a regra de dono vive no caso de uso.
- `ServiceOrderController.diagnose` fazia duas conversões de lista → foram para o
  request.
- `PaymentController` lia o repositório direto, pulando a camada de aplicação → agora
  passa pelo `PaymentUseCases`.
- `ProductController` montava o domínio com `.builder()` campo a campo e **devolvia a
  entidade de domínio como JSON** → `CreateProductRequest.toProduct()` e
  `ProductResponse.from(...)`.

**O que está bom (manter):** arquitetura hexagonal consistente; domínio rico onde
importa (máquinas de estado da OS e do pagamento, `Stock`); value objects (`Cpf`,
`Document`, `LicensePlate`); Saga orquestrada com DLQ, ShedLock e correlação por MDC;
comentários explicam o porquê.

**Estilo de caso de uso — padronizado: uma classe por caso de uso.** Os 4 serviços
seguem agora o padrão do os-service: uma classe `VerboSubstantivoUseCase` com um único
método `execute(...)`, recebendo só as dependências que usa.
- **billing:** `PaymentUseCases` virou `CreatePaymentUseCase`, `HandlePaymentNotificationUseCase`
  (webhook simulado), `ListPendingPaymentsUseCase`, `ReconcilePaymentUseCase`,
  `FindPaymentByServiceOrderUseCase`, `FindPaymentHistoryUseCase`, `RefundPaymentUseCase`;
  a regra comum de aprovar/recusar ficou em `PaymentDecisionRecorder` (package-private).
- **customer:** `ClientUseCases` → `Create/FindById/FindByDocument/List/Update/DeactivateClientUseCase`;
  `VehicleUseCases` → `Create/FindById/FindByPlate/ListByClient/Update/DeactivateVehicleUseCase`;
  `UserUseCases` → `SignUpUseCase` e `AuthenticateUserUseCase` (+ `BadCredentialsException`).
- **execution:** `ProductUseCases` → `Create/FindById/List/DeleteProductUseCase`;
  `StockUseCases` → `CreateStock`, `FindStockByProduct`, `ListStock`, `ListLowStock`,
  `RegisterStockEntry`, `RegisterStockExit`, `UpdateMinimumStock`; `ReservationUseCases` →
  `ReserveStock`, `ConfirmReservation`, `ReleaseReservation`, `FindReservationsByServiceOrder`,
  com a transição comum em `ReservationTransition` (package-private).
- Repetição de "busca ou 404" foi para métodos `default` nas portas (`getById`,
  `getByProductId`) em vez de um helper copiado em cada classe.

---

**Veredito (até a 3ª rodada):** saudável. Todos os achados "corrigir já" e "deveria corrigir" das três
rodadas estão resolvidos ou registrados como decisão com motivo. A 4ª rodada (acima) achou
3 pontos para corrigir já; os achados 2 a 4 foram corrigidos em 14/11. Para religar a AWS,
crie os secrets `MP_ACCESS_TOKEN` (obrigatório) e `ADMIN_INITIAL_PASSWORD` (recomendado).

**Não verificado:** não rodei os serviços juntos nem a Saga ponta a ponta na AWS; o job,
a nova cobrança e o estorno do Mercado Pago só foram testados contra a API simulada (os
testes não chamam a API real); o WriteConflict do MongoDB sob concorrência real não foi
reproduzido em teste; as cópias do contrato só ficam iguais se alguém rodar
`sync-saga-contract.sh`.
