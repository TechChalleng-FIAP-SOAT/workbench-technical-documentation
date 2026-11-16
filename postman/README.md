# Collections Postman — Plataforma Workbench (Fase 4)

Collections para exercitar a API dos microsserviços. Cada microsserviço tem a sua
collection no próprio repositório, em `postman/`; aqui fica a **collection unificada**
(todos os serviços + o fluxo Saga ponta a ponta).

## Arquivos

| Collection | Onde | Conteúdo |
|---|---|---|
| OS Service | `workbench-os-service/postman/` | Ordem de serviço, diagnóstico, decisão do orçamento, estado da Saga, serviços da OS, nova cobrança |
| Billing Service | `workbench-billing-service/postman/` | Orçamento, cobrança (captura `gatewayPaymentId`), histórico, webhook simulado (só local) |
| Execution Service | `workbench-execution-service/postman/` | Produtos, estoque e reservas |
| Customer Service | `workbench-customer-service/postman/` | Clientes e veículos |
| **Plataforma (todos)** | `workbench-technical-documentation/postman/` | Os 4 serviços + pasta "Fluxo Saga (E2E)" |
| Environment **Local** | `workbench-local.postman_environment.json` | Compose local: gateway `:8000`, serviços nas portas próprias, token de dev pronto |
| Environment **AWS** | `workbench-aws.postman_environment.json` | Tudo pelo API Gateway (os serviços têm NLB interno e não respondem direto) |

## Importar

No Postman: **Import** → selecione o arquivo `*.postman_collection.json`. (Também
funciona no Insomnia e no Bruno, que importam o formato Postman v2.1.)

## Environments

Importe o environment junto com a collection e selecione-o no canto superior direito:

- **Workbench - Local** — para o compose (`docker compose -f workbench-messaging/docker-compose.dev.yml --profile app up -d --build`).
  `gatewayUrl` = `http://localhost:8000` (nginx com o mesmo roteamento do API Gateway);
  os serviços também respondem direto (os `:8080`, customer `:8081`, billing `:8082`,
  execution `:8083`). O `token` vem **vazio**: gere um de ADMIN (seção "Gerar um token de dev" abaixo) e cole em `token`.
  Não há Lambda local: a pasta "Autenticação" só funciona na AWS.
- **Workbench - AWS** — preencha `gatewayUrl` com a `invoke_url` do `workbench-gateway`
  (`https://<api-id>.execute-api.us-east-1.amazonaws.com/main`) e `staffPassword` com o
  valor do secret `ADMIN_INITIAL_PASSWORD` (não é `admin123`). `customerUrl`, `osUrl`,
  `billingUrl` e `executionUrl` apontam para o próprio `gatewayUrl`: na AWS os serviços
  têm **NLB interno** e só o gateway é público. Rode **Autenticação → Login staff** para
  preencher `token` e **Login cliente** para preencher `clientToken`. CPF sem cadastro ou
  cliente inativo recebe o mesmo **401**.

> Na AWS o pagamento é pelo Mercado Pago: o passo "Webhook de pagamento" do Fluxo Saga
> só existe localmente (`PAYMENT_PROVIDER=fake`). Na AWS, abra o `checkoutUrl`, pague com
> um cartão de teste e espere ~30 s (o job de consulta confirma o pagamento).

## Variáveis

As collections usam variáveis de collection (edite em **Variables**), que o environment
selecionado sobrescreve:

- `token` — JWT (RS256) com role `ADMIN` ou `TECHNICIAN`. Os microsserviços **não
  emitem** token (isso é da Lambda de auth, a única com a chave privada); em dev, gere um
  token com a chave de dev da sua máquina (abaixo) e cole aqui.
- `baseUrl` (nas collections por serviço) — a porta local do serviço (os `8080`,
  customer `8081`, billing `8082`, execution `8083`); na AWS, a `invoke_url` do gateway.
- `customerUrl`, `osUrl`, `billingUrl`, `executionUrl` (na collection unificada) —
  um host/porta por serviço. Como o gateway roteia cada prefixo ao serviço dono, dá
  para apontar **as quatro para o gateway**:
  - local (`docker compose -f workbench-messaging/docker-compose.dev.yml --profile app up -d --build`):
    `http://localhost:8000` — ou direto nos serviços: os `:8080`, customer `:8081`,
    billing `:8082`, execution `:8083`;
  - AWS: a `invoke_url` do `workbench-gateway` (mesma do `gatewayUrl`) — já vem assim no
    environment AWS.

### Gerar um token de dev (JWT RS256)

Os tokens são RS256: a Lambda assina com a chave privada e os serviços só têm a pública. Em
dev, o par é gerado **por máquina** em `workbench-messaging/dev-keys/` (ignorado pelo git; a
primeira chamada de `dev-jwt.sh` cria o par). Para gerar um token de ADMIN (o `exp` abaixo é
2100; troque por um prazo menor se preferir):

```bash
cd workbench-messaging
bash -c 'source scripts/dev-jwt.sh; mint_dev_jwt "{\"sub\":\"admin@workbench.dev\",\"roles\":[\"ADMIN\"],\"exp\":4102444800}"'
```

Cole o resultado na variável `token`. Se você gerar um par novo (`scripts/dev-keys.sh --force`),
suba o compose de novo e gere outro token: o anterior deixa de valer.

## Fluxo Saga (E2E)

A pasta **"Fluxo Saga (E2E - caminho feliz)"** na collection unificada executa, em
ordem: cliente → veículo → produto → estoque → OS → diagnóstico (dispara a Saga) →
orçamento → estado da Saga → aprovar → `EM_EXECUCAO` → serviços `DOING`/`DONE` →
`PAGAMENTO_PENDENTE` → cobrança → webhook simulado (só local) → OS `ENTREGUE`.

- Rode pelo **Collection Runner** em ordem. Os ids (`clientId`, `productId`, `orderId`,
  `serviceId`, `gatewayPaymentId`) são capturados pelos scripts de teste.
- A Saga anda por mensageria (~5 s por passo): os passos 7, 13 e 15 já **esperam** antes de
  enviar (15 s, 8 s e 8 s). Se a máquina estiver lenta, ponha um *Delay* no Runner.
- Na AWS, pule o passo 14: abra o `checkoutUrl` do passo 13, pague com o cartão de teste e
  rode o 15 depois de ~30 s.
- Requer os 4 serviços e a mensageria (LocalStack) no ar — ver `workbench-messaging/docker-compose.dev.yml`.
- Para o fluxo completo automatizado (inclui recusa, falta de estoque e segurança), use
  `(cd workbench-messaging && bash e2e/saga-e2e.sh)`.

## Formatos que mudaram (se você tem uma cópia antiga importada)

| Request | Formato atual |
|---|---|
| Diagnóstico | `{"parts":[{"productId","quantity"}], "services":[{"serviceType","laborCost","useDefault"}]}` |
| Webhook simulado | `{"gatewayPaymentId": "...", "approved": true}` |
| Veículo `type` | `CAR`, `MOTORCYCLE`, `TRUCK` ou `VAN` |
| Produto `unit` | `UNIT`, `LITER`, `MILLILITER` ou `KILOGRAM` |
| Tipo de serviço | id é UUID (capturado em "Listar tipos de serviço") |

Reimporte as collections para pegar essas mudanças.
