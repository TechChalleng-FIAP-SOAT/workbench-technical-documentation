---
title: Saga Ponta a Ponta
tags:
  - como-rodar
  - saga
  - e2e
aliases:
  - SAGA-E2E-LOCAL
---

# Validar a Saga ponta a ponta (E2E) — local, sem AWS

> [!info] Antes dos comandos
> Os comandos usam duas variáveis do seu terminal. Defina uma vez por sessão:
> ```bash
> export WORKBENCH_DIR="<pasta onde estão os 11 repositórios workbench-*>"
> export TF_BUCKET="workbench-tfstate-<ID-da-conta-AWS>"   # bucket do state do Terraform
> ```

Guia passo a passo para subir os 4 microsserviços + mensageria (LocalStack) na sua
máquina e **demonstrar o fluxo da Saga** (caminho feliz e compensação). Serve como
roteiro para gravar o vídeo. Sem custo, sem AWS.
> [!tip] Versão automatizada
> Com a plataforma no compose (`docker-compose.dev.yml --profile app`), `workbench-messaging/e2e/saga-e2e.sh`
> executa estes mesmos cenários (caminho feliz, falta de estoque, pagamento recusado e segurança) e diz
> se passaram. Veja [[Rodando Testes]].

> **Pré-requisitos:** Docker rodando, Java 21, `curl` e `jq`. A infra de bancos usa
> o `workbench-messaging/docker-compose.dev.yml` (LocalStack + Postgres×3 + MongoDB).
> Para ver os logs no Datadog, o Datadog Agent instalado na máquina (opcional — Passo 0).

---

## Visão geral

Vamos subir, em ordem:
0. **(Opcional) Datadog**: ligar a coleta de logs do Agent *antes* de subir os serviços.
1. **Infra**: LocalStack (SNS/SQS) + bancos (docker-compose).
2. **Recursos da Saga** no LocalStack (tópicos/filas) via `bootstrap-localstack.sh`.
3. Os **4 serviços** Spring Boot, cada um numa porta, com a mensageria ligada.
4. Disparar o fluxo pela API e observar a OS percorrer os estados.

> **Ordem importa para o Datadog:** faça o Passo 0 (ligar o Agent) *antes* de subir
> os serviços no Passo 3. Os serviços gravam os logs JSON em `/tmp/workbench/` já no
> arranque; o Agent precisa estar coletando quando eles começam a escrever.

Cada serviço sobe na 8080 por padrão → vamos dar uma porta diferente a cada um.
Os quatro bancos sobem juntos pelo `docker-compose.dev.yml`:

| Serviço | Porta | Banco (container) |
|---|---|---|
| os-service | 8080 | Postgres :15432 (`workbench-os-db`) |
| customer-service | 8081 | Postgres :15434 (`workbench-customer-db`) |
| billing-service | 8082 | Postgres :15433 (`workbench-billing-db`) |
| execution-service | 8083 | MongoDB :27017 (`workbench-execution-mongo`) |

---

## Passo 0 — (Opcional) Ligar o Datadog para ver os logs

Pule este passo se não quiser enviar logs ao Datadog. Faça-o **uma única vez**; depois
é só deixar o Agent rodando. Requer o Datadog Agent já instalado (site US,
`datadoghq.com`). Todos os comandos abaixo precisam de `sudo` (config do sistema).

```bash
BASE="$WORKBENCH_DIR"

# 1) ligar a coleta de logs no Agent (troca "# logs_enabled: false" por "logs_enabled: true")
sudo sed -i '' 's/^# logs_enabled: false/logs_enabled: true/' /opt/datadog-agent/etc/datadog.yaml
grep -n "logs_enabled" /opt/datadog-agent/etc/datadog.yaml   # confira: logs_enabled: true (sem #)

# 2) instalar o check de logs do Workbench (mapeia cada arquivo -> service no Datadog)
sudo mkdir -p /opt/datadog-agent/etc/conf.d/workbench.d
sudo cp "$BASE/workbench-messaging/datadog/workbench-logs.conf.yaml" \
  /opt/datadog-agent/etc/conf.d/workbench.d/conf.yaml

# 3) pasta onde os serviços gravam os logs JSON (um arquivo por serviço)
mkdir -p /tmp/workbench

# 4) reiniciar o Agent e conferir a seção "Logs Agent"
sudo launchctl stop com.datadoghq.agent ; sleep 3 ; sudo launchctl start com.datadoghq.agent
sleep 10 ; sudo datadog-agent status | sed -n '/Logs Agent/,/^$/p'
```

Os 4 arquivos (`os-service.log`, `customer-service.log`, `billing-service.log`,
`execution-service.log`) só passam a existir/crescer **depois** que você subir cada
serviço (Passo 3) — é esperado que estejam ausentes agora.

> Depois de tudo no ar, no Datadog (Logs Explorer, US) filtre por `service:os-service`
> ou pelo fluxo de uma OS com `@service_order_id:<id-da-OS>`. Detalhes no Passo 8.

## Passo 1 — Subir a infra (bancos + LocalStack)

```bash
BASE="$WORKBENCH_DIR"
docker compose -f "$BASE/workbench-messaging/docker-compose.dev.yml" up -d
docker compose -f "$BASE/workbench-messaging/docker-compose.dev.yml" ps
```
Espere os 5 containers ficarem `healthy` (LocalStack, os-db, billing-db, customer-db,
execution-mongo). O `execution-mongo` demora um pouco mais porque inicia o replica set
no healthcheck.

## Passo 2 — Criar os tópicos/filas da Saga no LocalStack

```bash
cd "$BASE/workbench-messaging"
./bootstrap-localstack.sh
```
No fim ele lista as filas e tópicos. Os nomes (prefixo `workbench`) são:
- Tópicos SNS: `workbench-order-events`, `workbench-billing-events`, `workbench-execution-events`
- Filas SQS: `workbench-os-saga-replies-queue`, `workbench-billing-commands-queue`, `workbench-execution-commands-queue`

No LocalStack, o Account ID é sempre `000000000000` e o endpoint é `http://localhost:4566`.
Então os ARNs/URLs seguem este padrão fixo:

```
ARN tópico : arn:aws:sns:us-east-1:000000000000:<nome-do-topico>
URL fila   : http://localhost:4566/000000000000/<nome-da-fila>
```

> **Confira os nomes reais** (caso o prefixo mude) com:
> ```bash
> aws --endpoint-url=http://localhost:4566 sns list-topics --region us-east-1
> aws --endpoint-url=http://localhost:4566 sqs list-queues --region us-east-1
> ```

## Passo 3 — Subir os 4 serviços (um terminal por serviço)

Variáveis comuns aos serviços da Saga (os-service, execution, billing):
`MESSAGING_ENABLED=true`, `AWS_ENDPOINT=http://localhost:4566`, `AWS_REGION=us-east-1`,
`AWS_ACCESS_KEY_ID=test`, `AWS_SECRET_ACCESS_KEY=test`. O **customer-service não
participa da mensageria**, então não leva nenhuma dessas variáveis — só o datasource.

> **Datadog (logs):** cada comando abaixo inclui `LOG_JSON_FILE=/tmp/workbench/<serviço>.log`.
> É esse arquivo JSON que o Datadog Agent coleta (Passo 0). O valor já é o default do
> `logback-spring.xml`; está explícito aqui só para deixar claro. Se você NÃO ligou o
> Datadog (pulou o Passo 0), pode manter a variável mesmo assim — ela só grava um arquivo
> local, sem efeito colateral.

### Terminal A — customer-service (8081)
Suba primeiro: os outros o consultam. O banco é o `workbench-customer-db` (:15434),
que já subiu no Passo 1. Os valores abaixo são os defaults do `application.yml` —
explicitados aqui só para ficar claro.
```bash
cd "$BASE/workbench-customer-service"
SERVER_PORT=8081 \
LOG_JSON_FILE=/tmp/workbench/customer-service.log \
SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:15434/customer \
SPRING_DATASOURCE_USERNAME=dbadmin SPRING_DATASOURCE_PASSWORD=senha-super-segura \
./mvnw spring-boot:run
```

### Terminal B — execution-service (8083)
```bash
cd "$BASE/workbench-execution-service"
SERVER_PORT=8083 \
LOG_JSON_FILE=/tmp/workbench/execution-service.log \
MONGODB_URI=mongodb://localhost:27017/execution \
MESSAGING_ENABLED=true AWS_ENDPOINT=http://localhost:4566 AWS_REGION=us-east-1 \
AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test \
EXECUTION_EVENTS_TOPIC_ARN=arn:aws:sns:us-east-1:000000000000:workbench-execution-events \
EXECUTION_COMMANDS_QUEUE_URL=http://localhost:4566/000000000000/workbench-execution-commands-queue \
./mvnw spring-boot:run
```

### Terminal C — billing-service (8082)
```bash
cd "$BASE/workbench-billing-service"
SERVER_PORT=8082 \
LOG_JSON_FILE=/tmp/workbench/billing-service.log \
SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:15433/billing \
SPRING_DATASOURCE_USERNAME=dbadmin SPRING_DATASOURCE_PASSWORD=senha-super-segura \
MESSAGING_ENABLED=true AWS_ENDPOINT=http://localhost:4566 AWS_REGION=us-east-1 \
AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test \
BILLING_EVENTS_TOPIC_ARN=arn:aws:sns:us-east-1:000000000000:workbench-billing-events \
BILLING_COMMANDS_QUEUE_URL=http://localhost:4566/000000000000/workbench-billing-commands-queue \
PAYMENT_PROVIDER=fake \
./mvnw spring-boot:run
```

### Terminal D — os-service (8080, orquestrador)
`CUSTOMER_VALIDATION_ENABLED=true` liga o cliente REST para o Customer Service
(validação de cliente/veículo + resolução de e-mail para a notificação).
`NOTIFICATIONS_TOPIC_ARN` é o tópico dedicado de notificações de status.
```bash
cd "$BASE/workbench-os-service"
SERVER_PORT=8080 \
LOG_JSON_FILE=/tmp/workbench/os-service.log \
SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:15432/os_service \
SPRING_DATASOURCE_USERNAME=dbadmin SPRING_DATASOURCE_PASSWORD=senha-super-segura \
MESSAGING_ENABLED=true AWS_ENDPOINT=http://localhost:4566 AWS_REGION=us-east-1 \
AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test \
ORDER_EVENTS_TOPIC_ARN=arn:aws:sns:us-east-1:000000000000:workbench-order-events \
SAGA_REPLIES_QUEUE_URL=http://localhost:4566/000000000000/workbench-os-saga-replies-queue \
NOTIFICATIONS_TOPIC_ARN=arn:aws:sns:us-east-1:000000000000:workbench-os-notifications \
CUSTOMER_VALIDATION_ENABLED=true CUSTOMER_SERVICE_URL=http://localhost:8081 \
./mvnw spring-boot:run
```
Espere cada um imprimir `Started ...Application`.

---

## Passo 4 — Preparar dados base (outro terminal)

Token de ADMIN para as chamadas protegidas (dev). **Todos os serviços agora exigem
JWT** (customer, os, billing, execution) — exceto rotas públicas (login, health/swagger e o
webhook **simulado** de pagamento, que só existe localmente). O array `H` abaixo já inclui o
`Authorization`, então todas as chamadas deste guia que usam `"${H[@]}"` vão autenticadas. O
webhook simulado é chamado SEM token (rota pública no billing, só no perfil `local`).
```bash
# JWT staff ADMIN (RS256, chave de dev de workbench-messaging/dev-keys), válido até 2100.
export TOKEN='eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IndvcmtiZW5jaC1hdXRoIn0.eyJzdWIiOiJhZG1pbkB3b3JrYmVuY2guZGV2Iiwicm9sZXMiOlsiQURNSU4iXSwiZXhwIjo0MTAyNDQ0ODAwfQ.PDsG3cX4EXmwtXKs3a21McMxEy-wO16cb0IKs8YgLj4SW22cOknv4okyBP0UBioo9_k58jqfEdhwkJhnc12a9wvdAO8cYOR6v7eiMkTt8sslMC95ulihJSA6p1KOtKnLzA8ThTW53d14gG-SdsUMf-7Va1Z0Yn6xCRW7MTUvcpu_SzauozapGMMn5514NouKCktEzi_oO2XrKBVNkPXv1o8bLUsNX56nLUY-OWsktfLVAnk4Ql7sOp2KM2iSRR2cMrJdVaunCqvhvIhnZzzvXAI9a-wJHogNuY-oZ0kD1rNxWuVNaoTWun-S8tMXe694TQsTxraoiUt6YQ3MobL38A'
H=(-H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json")
```

Cliente + veículo (customer-service, 8081). Capturamos o `clientId` da resposta:
```bash
# cria o cliente; se já existir (409 — documento tem índice único), busca o id por documento
export CLIENT_ID=$(curl -s "${H[@]}" -X POST http://localhost:8081/api/clients \
  -d '{"name":"Maria Oliveira","document":"52998224725","email":"maria@example.com","phone":"11999990000"}' \
  | jq -r '.id')
if [ "$CLIENT_ID" = "null" ] || [ -z "$CLIENT_ID" ]; then
  CLIENT_ID=$(curl -s "${H[@]}" http://localhost:8081/api/clients/document/52998224725 | jq -r '.id')
fi
echo "CLIENT_ID=$CLIENT_ID"
curl -s "${H[@]}" -X POST http://localhost:8081/api/vehicles \
  -d "{\"clientId\":$CLIENT_ID,\"plate\":\"ABC-1234\",\"brand\":\"VW\",\"model\":\"Gol\",\"year\":2018,\"color\":\"Prata\",\"type\":\"CAR\"}" | jq
```

Produto + estoque (execution-service, 8083). O `productId` é gerado pelo serviço,
então capturamos da resposta:
```bash
# SKU único por execução (o sku é único: recriar com o mesmo SKU devolve 409).
# Se for rodar uma vez só, pode fixar "OLEO-5W30".
SKU="OLEO-5W30-$(date +%s)"
export PROD=$(curl -s "${H[@]}" -X POST http://localhost:8083/api/products \
  -d "{\"name\":\"Óleo 5W30\",\"sku\":\"$SKU\",\"type\":\"PART\",\"unit\":\"UNIT\",\"category\":\"Lubrificantes\",\"brand\":\"Mobil\",\"costPrice\":25.00,\"salePrice\":45.00,\"warrantyMonths\":6,\"fractionalAllowed\":false,\"packageSize\":1}" \
  | jq -r '.id')
echo "PROD=$PROD"
curl -s "${H[@]}" -X POST http://localhost:8083/api/stocks \
  -d "{\"productId\":\"$PROD\",\"quantity\":100,\"minimumQuantity\":10}" | jq
```

---

## Passo 5 — Caminho feliz da Saga

### 5.1 Criar a OS (os-service, 8080)
```bash
curl -s "${H[@]}" -X POST http://localhost:8080/order \
  -d '{"cpfCnpj":"52998224725","placaVeiculo":"ABC-1234","serviceTypes":["TROCA_OLEO"]}' | jq
export OS=$(curl -s "${H[@]}" http://localhost:8080/order | jq -r '.[0].id')
echo "OS=$OS"
```

### 5.2 Registrar diagnóstico → dispara a Saga (reserva de estoque)
O payload usa `parts` (peças a reservar) e `services` (mão de obra, campo
`serviceType`):
```bash
curl -s "${H[@]}" -X POST http://localhost:8080/order/$OS/diagnosis \
  -d "{\"parts\":[{\"productId\":\"$PROD\",\"quantity\":2}],\"services\":[{\"serviceType\":\"TROCA_OLEO\",\"laborCost\":80.00,\"useDefault\":false}]}" | jq
```
Nos bastidores (assíncrono, ~segundos): OS → `ComandoReservarEstoque` → Execution
reserva → `ReservaConfirmada` → OS pede orçamento → Billing gera → `OrcamentoGerado`
→ OS vai para `AGUARDANDO_APROVACAO`.

### 5.3 Conferir que chegou em AGUARDANDO_APROVACAO
```bash
curl -s "${H[@]}" http://localhost:8080/order/id/$OS | jq '.serviceStatus'
# e o orçamento no billing:
curl -s "${H[@]}" http://localhost:8082/api/budgets/service-order/$OS | jq
```

### 5.4 Aprovar o orçamento → confirma reserva (baixa de estoque)
```bash
curl -s "${H[@]}" -X POST http://localhost:8080/order/$OS/decision -d '{"decision":"APPROVED"}'
curl -s "${H[@]}" http://localhost:8080/order/id/$OS | jq '.serviceStatus'   # -> APROVADO
```

### 5.5 Executar os serviços → FINALIZADA → PAGAMENTO_PENDENTE (operação da oficina)
Depois de APROVADO, a Saga **pausa**: fazer o serviço é operação do staff. A OS entra em
execução pelo `PATCH /order/{id}` e **cada serviço** da OS anda `TO_DO → DOING → DONE`;
quando o último fica `DONE`, a OS vai sozinha para `FINALIZADA` (e o tempo de execução
alimenta o `/monitoring`).
```bash
curl -s "${H[@]}" -X PATCH http://localhost:8080/order/$OS -d '{"status":"EM_EXECUCAO"}'

# serviços da OS (um por tipo pedido na abertura)
curl -s "${H[@]}" http://localhost:8080/order/$OS/services | jq
for SV in $(curl -s "${H[@]}" http://localhost:8080/order/$OS/services | jq -r '.[].id'); do
  curl -s "${H[@]}" -X PATCH http://localhost:8080/order/$OS/services/$SV/status -d '{"status":"DOING"}' >/dev/null
  curl -s "${H[@]}" -X PATCH http://localhost:8080/order/$OS/services/$SV/status -d '{"status":"DONE"}' | jq '.status'
done
curl -s "${H[@]}" http://localhost:8080/order/id/$OS | jq '.serviceStatus'   # -> FINALIZADA

curl -s "${H[@]}" -X PATCH http://localhost:8080/order/$OS -d '{"status":"PAGAMENTO_PENDENTE"}'
curl -s "${H[@]}" http://localhost:8080/order/id/$OS | jq '.serviceStatus'   # -> PAGAMENTO_PENDENTE
```
> Pular etapas é recusado: OS fora de ordem → `422`; serviço pulando `DOING` → `422`;
> `PATCH` da OS para `FINALIZADA` com serviço ainda pendente → `409`. O `PATCH` da OS
> retorna `204 No Content` em caso de sucesso.
>
> **Cobrança automática:** ao entrar em `PAGAMENTO_PENDENTE`, o os-service dispara
> automaticamente `ComandoCobrarPagamento` na Saga, e o Billing cria a cobrança
> (status `PENDENTE`) sem você precisar chamar nada. Aguarde ~2-3s e confira no Billing:
> ```bash
> sleep 3
> curl -s "${H[@]}" http://localhost:8082/api/payments/service-order/$OS | jq
> ```

### 5.6 Confirmar pagamento (webhook do billing) → OS PAGA/ENTREGUE
A cobrança já foi criada automaticamente (5.5). Pegue o `gatewayPaymentId` dela e
confirme o pagamento via webhook simulado. Na AWS isso não existe: com o Mercado Pago um job do
billing consulta o pagamento a cada 30 s.
```bash
# 1) obtém o gatewayPaymentId da cobrança criada automaticamente pela Saga
export GPID=$(curl -s "${H[@]}" http://localhost:8082/api/payments/service-order/$OS \
  | jq -r '.gatewayPaymentId')
echo "gatewayPaymentId=$GPID"

# 2) confirma via webhook — o payload é {gatewayPaymentId, approved}
curl -s -X POST http://localhost:8082/api/payments/webhook -H "Content-Type: application/json" \
  -d "{\"gatewayPaymentId\":\"$GPID\",\"approved\":true}"

# aguarde ~2-3s (a confirmação é assíncrona: billing publica PagamentoConfirmado na Saga)
sleep 3
curl -s "${H[@]}" http://localhost:8080/order/id/$OS | jq '.serviceStatus'   # -> ENTREGUE
```
> **O que o webhook faz:** `POST /api/payments/webhook` simula a notificação de um gateway
> e **só existe com `PAYMENT_PROVIDER=fake`**, que só sobe no perfil `local` (o
> `FakeProviderGuard` barra o início do serviço em qualquer outro caso). Na AWS não há webhook:
> o Mercado Pago é consultado pelo `PaymentStatusPollingJob`. O billing marca o pagamento como `PAGAMENTO_APROVADO` e **publica
> `PagamentoConfirmado` na Saga**; o os-service, ao recebê-lo, avança a OS
> `PAGAMENTO_PENDENTE → PAGO → ENTREGUE`. A resposta HTTP do webhook é só `200`; o avanço
> da OS acontece em seguida, de forma assíncrona. O webhook é **idempotente**: reenviar a
> mesma confirmação não causa erro. Payload: `{"gatewayPaymentId": "...", "approved": true|false}`.
>
> **Importante:** o webhook só faz a OS avançar se ela estiver em `PAGAMENTO_PENDENTE`.

---

## Passo 6 — Compensação (rollback)

Repita 5.1 e 5.2 para criar uma **nova OS** em `AGUARDANDO_APROVACAO`, e então
**recuse** o orçamento:
```bash
curl -s "${H[@]}" -X POST http://localhost:8080/order/$OS2/decision \
  -d '{"decision":"REJECTED","reason":"Cliente nao aprovou"}'
```
Nos bastidores: OS → `ComandoLiberarReserva` → Execution **libera o estoque**
(`ReservaLiberada`) → OS vai para `RECUSADA`. Confira:
```bash
curl -s "${H[@]}" http://localhost:8080/order/id/$OS2 | jq '.serviceStatus'   # -> RECUSADA
curl -s "${H[@]}" "http://localhost:8083/api/stocks/product/$PROD" | jq
# a quantidade reservada deve ter voltado ao disponível
```

---

## Passo 7 — Evidências para o vídeo

- Logs dos 4 terminais mostrando a conversa da Saga (procure por `saga` / `Comando` /
  `Reserva` / `Orcamento` nos logs — cada passo é logado).
- As filas no LocalStack recebendo mensagens:
  ```bash
  aws --endpoint-url=http://localhost:4566 sqs list-queues --region us-east-1
  ```
- Os estados da OS mudando a cada etapa (as respostas dos `curl` acima).

---

## Passo 8 — Ver os logs no Datadog (local)

Pré-requisito: Agent ligado no **Passo 0** e serviços subidos no **Passo 3** com
`LOG_JSON_FILE` (eles gravam JSON em `/tmp/workbench/<serviço>.log`; o Agent coleta
esses arquivos). Aqui é só validar e buscar.

### 8.1 Confirmar que os serviços estão gravando
```bash
ls -l /tmp/workbench/                      # 4 arquivos, crescendo
tail -f /tmp/workbench/os-service.log      # deve mostrar JSON de verdade (Ctrl+C p/ sair)
```
Se só existir o arquivo com `"message":"ping"` (teste) ou os arquivos não crescerem, os
serviços foram subidos **antes** do logback novo — pare e suba de novo (Passo 3).

### 8.2 Confirmar que o Agent está coletando
```bash
sudo datadog-agent status | sed -n '/Logs Agent/,/^$/p'
```
Os 4 arquivos devem aparecer com `Type: file` e `Status: OK` (integração `workbench`).
"Backpressure" no cabeçalho é só um indicador de buffer, não é erro.

### 8.3 Buscar no Datadog (Logs Explorer, site US)
- Por serviço: `service:os-service` (ou customer/billing/execution).
- O fluxo de uma OS ponta a ponta: `@service_order_id:<id-da-OS>` (cada passo da Saga
  carrega essa chave no MDC, atravessando os serviços). `@saga_id:<sagaId>` filtra uma
  **rodada** da Saga — um novo diagnóstico gera outro `sagaId`. O valor está no campo
  `saga_id` de qualquer linha de log da OS.
- Correlação de uma requisição: `@request_id:<valor>`.

> **Nada aparece no Datadog?** (1) `sudo datadog-agent status` deve listar os 4 arquivos
> em *Logs Agent* sem erro; (2) os arquivos em `/tmp/workbench/` devem estar crescendo;
> (3) confirme `logs_enabled: true` em `/opt/datadog-agent/etc/datadog.yaml` (Passo 0);
> (4) lembre que isso envia os logs locais para a sua conta Datadog — use só em dev.

---

## Encerrar

Pare os serviços (Ctrl+C em cada terminal) e derrube a infra:
```bash
# para e remove os 5 containers (mantém os volumes/dados)
docker compose -f "$BASE/workbench-messaging/docker-compose.dev.yml" down

# para zerar também os dados dos bancos, acrescente -v:
docker compose -f "$BASE/workbench-messaging/docker-compose.dev.yml" down -v

cd "$BASE/workbench-messaging" && bash ./bootstrap-localstack.sh destroy   # opcional
```

---

## Dicas de troubleshooting

- **Serviço não sobe / porta ocupada:** confira se não há outra instância na mesma
  porta (`lsof -ti tcp:8080`). Use `SERVER_PORT` diferente por serviço.
- **OS não avança de EM_DIAGNOSTICO:** verifique se os 4 serviços estão no ar com
  `MESSAGING_ENABLED=true` e os mesmos ARNs/URLs; confira as filas no LocalStack.
- **`cliente/veículo não encontrado` ao criar OS:** o customer-service precisa estar
  no ar (8081) com `CUSTOMER_VALIDATION_ENABLED=true` apontando para ele, e o
  cliente/veículo devem ter sido criados no Passo 4.
- **Mensagens presas:** há DLQ por fila; reprocessar exige limpar as filas
  (`./bootstrap-localstack.sh destroy` + rodar de novo).
