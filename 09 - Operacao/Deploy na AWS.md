---
title: Deploy na AWS
tags:
  - operacao
  - aws
  - deploy
aliases:
  - DEPLOY-AWS-GUIA
---

# Guia de Deploy na AWS — Plataforma Workbench (Fase 4)

> [!info] Antes dos comandos
> Os comandos usam duas variáveis do seu terminal. Defina uma vez por sessão:
> ```bash
> export WORKBENCH_DIR="<pasta onde estão os 11 repositórios workbench-*>"
> export TF_BUCKET="workbench-tfstate-<ID-da-conta-AWS>"   # bucket do state do Terraform
> ```

Passo a passo completo para **ligar** a stack na AWS, **testar/gravar o vídeo** e
**desligar** (destruir tudo para parar a cobrança). Cada passo explica *o que é*,
*por que usamos no projeto* e *o que faz*.

> **Estratégia:** ligar → testar → destruir no mesmo dia. O EKS não tem "pausar":
> ou está criado (cobrando) ou destruído. Custo estimado com tudo ligado:
> **~US$ 7–10/dia** (estimativa: EKS control plane ~US$0,10/h + NAT Gateway ~US$0,045/h +
> 2× nós t3.small + 3× RDS db.t3.micro + 4 NLBs internos; a chave KMS dos tópicos soma ~US$ 1/mês).
>
> **Recriação:** os endpoints do RDS e os DNS dos NLBs mudam a cada vez que a stack é
> recriada. Depois da FASE 3, atualize os `DB_URL_*_MAIN`; depois da FASE 6, o
> `CUSTOMER_SERVICE_URL_MAIN` (FASE 8).
>
> **Modelo de execução:** ligar via **pipeline** (GitHub Actions) — cumpre o
> requisito "deploy automatizado" do PDF; desligar via **terminal** (`terraform
> destroy`) — mais seguro e imediato.

---

## 0. Conceitos (para entender o que estamos fazendo)

| Termo | O que é | Por que usamos |
|---|---|---|
| **Terraform** | Ferramenta de Infraestrutura como Código (IaC). Você descreve a infra em arquivos `.tf` e ela cria/destrói na AWS. | Cria VPC, EKS, RDS etc. de forma reproduzível e destruível com um comando. |
| **State (S3)** | Arquivo `terraform.tfstate` que registra tudo que o Terraform criou. Guardado num bucket S3 (`workbench-tfstate-<ID-da-conta>`). | É a "memória" do Terraform — sem ele não dá pra atualizar nem destruir com segurança. |
| **VPC** | Rede virtual privada na AWS (subnets, NAT, rotas). | Onde o cluster e o banco vivem, isolados da internet pública. |
| **EKS** | Kubernetes gerenciado pela AWS. | Onde os 4 microsserviços rodam (requisito do PDF: deploy em Kubernetes). Cluster: `workbench-platform-main`. |
| **RDS PostgreSQL** | Banco relacional gerenciado. | **Uma instância por serviço** (os-service, billing, customer) — banco próprio por serviço (SQL), requisito do PDF. |
| **MongoDB Atlas** | Banco NoSQL gerenciado (externo à AWS, free tier). | Banco próprio do execution-service (**NoSQL**, requisito do PDF). Não roda no cluster. |
| **SNS/SQS** | Mensageria (tópicos/filas). | Transporte assíncrono da Saga entre os microsserviços. |
| **Lambda + API Gateway** | Funções serverless + porta de entrada HTTP. | Autenticação: Lambda emite JWT de **cliente** (CPF) e de **staff** (e-mail/senha) e valida o token; API Gateway roteia e protege as rotas (`/auth` cliente, `/auth/login` staff). |
| **Pipeline (GitHub Actions)** | Automação de CI/CD. | "Deploy automatizado" exigido pelo PDF: um merge na `main` dispara o `terraform apply`. |

**Ordem obrigatória** (cada camada depende da anterior):

```
1. k8s-terraform (VPC + EKS + permissão SNS/SQS dos nós) → pipeline
2. [VOCÊ] outputs → secrets                              → GitHub (manual)
3. database (RDS, 3 instâncias)                          → pipeline
3.1 MongoDB Atlas (NoSQL)                                → painel Atlas (manual, 1x)
4. messaging (SNS/SQS + alarmes das DLQs)                → terminal (não tem pipeline)
5. lambda (auth) com URL provisória do customer          → pipeline
6. 4 microsserviços (deploy no EKS)                      → pipeline (USE_AWS=true)
7. gateway (API Gateway + VPC Link)                      → pipeline — DEPOIS da 6
8. lambda de novo, com o DNS do NLB interno do customer  → pipeline
```

> **Por que o gateway vem depois dos serviços:** os serviços têm **NLB interno** (não
> ficam na internet) e o gateway chega até eles por **VPC Link**, encontrando cada NLB pela
> tag. Sem os serviços no ar, não há NLB para encontrar.

---

## 1. Pré-requisitos (já feitos ✅)

- [x] Conta AWS acessível (root) + usuário IAM `<usuario-iam-admin>` com AdministratorAccess.
- [x] Access Keys do `<usuario-iam-admin>` configuradas no terminal (`aws configure`).
  - Verificar: `aws sts get-caller-identity` → deve mostrar `Account: <ID-da-conta>`.
- [x] Terraform e Helm instalados (`terraform version`, `helm version --short`).
- [x] Bucket S3 do state criado: **`workbench-tfstate-<ID-da-conta>`** (versionado).
- [x] Secrets na org GitHub `TechChalleng-FIAP-SOAT`:
  `TF_STATE_BUCKET_MAIN`, `AWS_ACCOUNT_ID_MAIN`, `AWS_REGION`,
  `AWS_ACCESS_KEY_ID_MAIN`, `AWS_SECRET_ACCESS_KEY_MAIN`.

---

## FASE 1 — Ligar o k8s-terraform (VPC + EKS) 🟢 começa a cobrança

**O que faz:** cria a rede (VPC, subnets, NAT) e o cluster Kubernetes (EKS) +
node group + metrics-server, e dá aos nós a permissão de **publicar no SNS e ler do SQS**
(`workbench-*`) e de usar a chave KMS dos tópicos (só via SNS), que os pods usam na Saga.
É a base de tudo.

> **Cluster já criado antes da permissão de SNS/SQS?** Rode o CD do `k8s-terraform` de
> novo depois de mergear a mudança: o `apply` só cria a policy e a anexa à role dos nós
> (sem recriar nós). Sem ela, a Saga não anda na AWS (`AccessDenied` no log dos serviços).

> **Nada muda aqui para as 3 instâncias RDS nem para o Atlas.** O `k8s-terraform` já
> expõe os outputs que o `workbench-database` consome via `terraform_remote_state`
> (`vpc_id`, `private_subnet_ids`, `node_security_group_id`, `region`), e o SG dos nós
> do EKS já tem egress liberado — a regra de ingress 5432 fica no SG de cada instância
> RDS (criado no `workbench-database`). O Atlas é externo à AWS e não depende desta fase.

**Como ligar (pipeline):**
1. Acesse: https://github.com/TechChalleng-FIAP-SOAT/workbench-k8s-terraform/actions
2. Clique no workflow **CD** no menu esquerdo.
3. Abra a execução mais recente.
4. Canto superior direito → **Re-run jobs → Re-run all jobs**.
   - *Por quê re-run:* a pipeline dispara por push na `main`; como o código já
     está na `main` e os secrets agora existem, re-executar roda o `apply` de fato.

**Tempo:** ~15–20 min. **Sucesso:** job verde; step final imprime `cluster_name`
e `vpc_id`.

**Se falhar:** me diga o nome do step vermelho. Causas comuns: secret ausente
(revisar Fase 0) ou versão do EKS (o Terraform não volta versão — se reclamar,
ajustar `cluster_version` em `variables.tf`).

---

## FASE 2 — Copiar outputs e criar os secrets do banco 🟡 manual

**Por que:** o database/lambda precisam saber em qual VPC/subnets criar os
recursos. Esses IDs só existem depois da Fase 1.

**Pegar os valores (terminal):**
```bash
cd "$WORKBENCH_DIR/workbench-k8s-terraform"
terraform init -input=false \
  -backend-config="bucket=${TF_BUCKET}" \
  -backend-config="key=k8s/main/terraform.tfstate" \
  -backend-config="region=us-east-1" \
  -backend-config="encrypt=true"

terraform output -raw vpc_id                 # ex.: vpc-0abc123...
terraform output -json private_subnet_ids    # ex.: ["subnet-aaa","subnet-bbb"]
terraform output -raw node_security_group_id # ex.: sg-0def456...
```

**Criar os secrets na org** (https://github.com/organizations/TechChalleng-FIAP-SOAT/settings/secrets/actions → *New organization secret*):

| Secret | Valor | Usado por |
|---|---|---|
| `VPC_ID_MAIN` | o `vpc_id` | database, lambda |
| `SUBNET_IDS_MAIN` | os private subnets, formato `["subnet-aaa","subnet-bbb"]` | database, lambda |
| `VPC_SECURITY_GROUP_IDS_MAIN` | o `node_security_group_id`, formato `["sg-0def456"]` | lambda |
| `MP_ACCESS_TOKEN` | Access Token **de teste** do Mercado Pago (começa com `APP_USR-`, em *Suas integrações → sua aplicação → Credenciais de teste*; tipo de API **Preferências**). **Obrigatório**: o deploy do billing falha sem ele | billing |
| `ADMIN_INITIAL_PASSWORD` | **necessário no 1º deploy** — senha forte (≥8) que substitui a padrão `admin123` do `admin@workbench.dev` no 1º start do customer-service. Enquanto o admin estiver com `admin123`, o serviço não sobe sem ele; depois da troca, pode faltar | customer |
| `DB_PASSWORD_OS` | senha forte da instância do OS Service | database |
| `DB_PASSWORD_BILLING` | senha forte da instância do Billing | database |
| `DB_PASSWORD_CUSTOMER` | senha forte da instância do Customer | database |
| `DB_USERNAME_OS` / `_BILLING` / `_CUSTOMER` | (opcional) usuário master por instância; default = `os_service` / `billing` / `customer`. Começa com letra, só letras/números/`_` (**sem hífen**), até 63 chars. NÃO use admin/postgres/root nem o identificador da instância | database |
| `JWT_SECRET` | string ≥32 chars, **a mesma** usada nos apps e na Lambda | lambda, apps |

> O pipeline cria **uma instância por serviço**: `workshop-os-service-main`,
> `workshop-billing-main`, `workshop-customer-main` (identificadores derivados
> automaticamente de `name_prefix` + serviço + ambiente). Esses são os **nomes das
> instâncias**, não usernames — não os coloque em `DB_USERNAME_*` (o hífen é inválido
> para usuário e o RDS falha com `Invalid master user name`). A rede é resolvida do estado
> remoto do `k8s-terraform` (`TF_VAR_k8s_remote_state_bucket`); `VPC_ID_MAIN`/
> `SUBNET_IDS_MAIN` seguem como fallback.

---

## FASE 3 — Ligar o database (RDS PostgreSQL, uma instância por serviço)

**O que faz:** cria **três instâncias** RDS PostgreSQL (`db.t3.micro`), uma por
serviço (OS, Billing, Customer), cada uma com seu subnet group, security group,
database e credencial próprios.

**Antes de ligar, confira os secrets `DB_USERNAME_*`:** devem ser `os_service`,
`billing` e `customer` (ou não existir — o pipeline usa esses valores como default).
**Não** use `workshop-os-service-main` etc.: isso é o nome da instância, e o hífen
faz o RDS falhar com `Invalid master user name`.

**Como ligar (pipeline):** o pipeline dispara por push na `main`:
1. Mergeie o PR pendente do `workbench-database` na `main` (o merge gera o push que dispara).
2. Ou, se não houver nada para mergear, use Actions → workflow → **Re-run all jobs**.

**Tempo:** ~8–15 min (3 instâncias em paralelo). **Sucesso:** o job termina verde e as
3 instâncias aparecem como `available` no console do RDS.

**Erros conhecidos:**
- `FreeTierRestrictionError ... backup retention period` → conta no plano Free aceita
  no máximo 1 dia de backup. Já corrigido no código (`backup_retention_period = 1`).
- `Invalid master user name` → valor inválido em `DB_USERNAME_*` (ver acima).

**Depois:** crie **um secret de URL por serviço** (cada app conecta só na sua instância):

| Secret | Valor |
|---|---|
| `DB_URL_OS_MAIN` | `jdbc:postgresql://<endpoint-os-service>:5432/os_service` |
| `DB_URL_BILLING_MAIN` | `jdbc:postgresql://<endpoint-billing>:5432/billing` |
| `DB_URL_CUSTOMER_MAIN` | `jdbc:postgresql://<endpoint-customer>:5432/customer` |

Pegue todas de uma vez pelo output do Terraform. Primeiro conecte o Terraform local ao
state remoto da `main` (só leitura; não muda nada na AWS):
```bash
cd "$WORKBENCH_DIR/workbench-database/infra/terraform"
terraform init -input=false -reconfigure \
  -backend-config="bucket=${TF_BUCKET}" \
  -backend-config="key=workbench-database/main/terraform.tfstate" \
  -backend-config="region=us-east-1" -backend-config="use_lockfile=true"
terraform output -json service_jdbc_urls
```
Sai um JSON `{"billing":"jdbc:postgresql://...:5432/billing", "customer": ..., "os_service": ...}`
— cada valor é exatamente o conteúdo do secret `DB_URL_*_MAIN` correspondente.

Alternativa sem Terraform (só AWS CLI) — lista o endpoint de cada instância; monte a
URL como `jdbc:postgresql://<endpoint>:5432/<banco>`:
```bash
aws rds describe-db-instances --region us-east-1 \
  --query "DBInstances[?starts_with(DBInstanceIdentifier,'workshop-')].[DBInstanceIdentifier,Endpoint.Address]" \
  --output table
```

Cada serviço recebe, no seu `k8s/secret.yaml`, o `SPRING_DATASOURCE_URL` da **sua**
instância e as credenciais da **sua** instância (`DB_USERNAME_*`/`DB_PASSWORD_*`) —
reforçando que nenhum serviço acessa o banco de outro.

---

## FASE 3.1 — MongoDB Atlas (banco NoSQL do execution-service)

**O que faz:** provê o banco **NoSQL** do `execution-service`. Usamos **MongoDB Atlas**
(gerenciado, free tier `M0`, US$ 0) em vez de um Mongo no cluster — nenhum Mongo roda
no EKS em produção. Não há Terraform aqui: o Atlas é criado no painel, **uma única vez**.

**Passos (painel do Atlas — https://cloud.mongodb.com):**
1. Crie um projeto e um **cluster free `M0`** (provider AWS, região `us-east-1` de
   preferência, para baixa latência com o EKS). ✅ Já criado: **`fiap-db-mongo`**.
   Na tela do cluster, *Backups OFF* / *Auto-scaling OFF* são normais no M0 — não mexa.
2. **Security → Database Access → Add New Database User:** método *Password*,
   username `execution`, **Autogenerate Secure Password** (copie na hora — não aparece
   de novo; se digitar à mão, evite `@ : / ? #`), role **Read and write to any
   database** → *Add User*.
3. **Security → Network Access → Add IP Address → Allow Access from Anywhere**
   (`0.0.0.0/0`). Sem isso os pods do EKS não conectam. O cluster continua protegido
   por usuário/senha; para endurecer, libere só o IP do NAT Gateway da VPC.
4. **Connect → Drivers → Java:** copie a string
   `mongodb+srv://execution:<db_password>@fiap-db-mongo.xxxxx.mongodb.net/?retryWrites=true&w=majority&appName=fiap-db-mongo`
   e ajuste: troque `<db_password>` pela senha do passo 2 e insira o banco antes do
   `?` → `...mongodb.net/execution?retryWrites=...`.

> O Atlas M0 **não gera custo** e pode ficar criado entre um teste e outro — só a AWS
> precisa ser destruída.

**Depois:** crie o secret com a URI para o app:

| Secret | Valor |
|---|---|
| `MONGODB_URI` | `mongodb+srv://<user>:<senha>@<cluster>.mongodb.net/execution?retryWrites=true&w=majority` |

> O `execution-service/k8s/secret.yaml` traz `MONGODB_URI: REPLACE_ME`; o valor real é
> injetado pela pipeline no deploy (passo que cria o Secret a partir do secret da org
> `MONGODB_URI`), nunca commitado. Para rodar no cluster **sem**
> Atlas (teste), aplique `kubectl apply -f k8s/mongo-local.yaml` e use
> `mongodb://execution-mongo:27017/execution`.

---

## FASE 4 — Ligar o messaging (SNS/SQS) 🟡 terminal (sem pipeline)

**O que faz:** cria os tópicos SNS e filas SQS da Saga na AWS real, cifrados (chave KMS
própria nos tópicos, ~US$ 1/mês; criptografia do SQS nas filas), e os alarmes das DLQs.

**Por que no terminal:** este repo não tem workflow de CI/CD; é aplicado
manualmente (o padrão dele é LocalStack; com `use_localstack=false` vai pra AWS).

```bash
cd "$WORKBENCH_DIR/workbench-messaging"
terraform init -input=false \
  -backend-config="bucket=${TF_BUCKET}" \
  -backend-config="key=messaging/main/terraform.tfstate" \
  -backend-config="region=us-east-1" \
  -backend-config="encrypt=true"

# notification_email (opcional): e-mail inscrito no tópico de notificação de
# status da OS ao cliente. A AWS envia um e-mail de confirmação que precisa ser
# aceito. Omita para criar só o tópico, sem subscription.
terraform apply -var "use_localstack=false" -var "environment=main" \
  -var "notification_email=seu-email@exemplo.com" \
  -var "alert_email=seu-email@exemplo.com"
# revise o plano e digite: yes
```

**Sucesso:** `terraform output` lista os ARNs/URLs das filas, o `notifications_topic_arn`
e o `alerts_topic_arn`. **Não precisa copiar nada para os apps:** o pipeline de cada
serviço monta os ARNs e as URLs com a conta e a região do deploy (nomes `workbench-*`) num
ConfigMap `<serviço>-runtime`, com `MESSAGING_ENABLED=true`. **Confirme a subscription no
seu e-mail** (link que a AWS envia), senão o SNS não entrega.

O `alert_email` recebe os **alarmes das DLQs** (um alarme do CloudWatch por DLQ, que
dispara com a 1ª mensagem que cair nela). Também precisa confirmar a inscrição. O que
fazer quando chegar um alarme está no [[Runbook]].

### E-mail ao cliente pelo SES (opcional)

Sem isto, o e-mail sai pelo tópico SNS e chega **só ao endereço inscrito** (`notification_email`),
e não ao cliente. Com o SES, o os-service envia direto ao e-mail cadastrado do cliente.

1. **Remetente e destinatários.** No `terraform apply` da FASE 4, acrescente:
   ```bash
   -var "ses_sender_email=oficina@seu-dominio.com" \
   -var 'ses_verified_recipients=["seu-email-de-teste@exemplo.com"]'
   ```
   A AWS manda um e-mail de verificação para **cada** endereço; o dono precisa abrir o link. Sem
   isso o envio é recusado.
2. **Sandbox.** Uma conta nova do SES só envia **de remetente verificado para destinatário
   verificado**. Por isso `ses_verified_recipients` precisa ter o e-mail **cadastrado do cliente** de teste
   (o do Customer Service). Para mandar a qualquer cliente, peça ao SES o **acesso à produção**
   (console do SES, solicitação manual).
3. **Ligar no serviço.** Crie o secret da org `SES_SENDER_EMAIL` com o **mesmo** remetente. A pipeline
   do os-service troca para `NOTIFICATION_CHANNEL=ses` sozinha quando ele existe; sem o secret, fica
   no SNS. Com `ses` e sem remetente o pod **não sobe** (`CrashLoopBackOff`), de propósito.
4. **Permissão.** `ses:SendEmail` nas identidades da conta já vem no `workbench-k8s-terraform`. Se o
   cluster foi criado antes disso, rode o CD dele de novo.

Cliente **sem e-mail cadastrado** não recebe nada (fica no log). Falha de envio nunca reverte a OS.
Este caminho **não foi testado contra o SES real** (o LocalStack da comunidade não tem SES).

---

## FASE 5 — Ligar o lambda (autenticação)

**O que faz:** cria as **3 funções Lambda** — emissor de JWT de cliente (`/auth`),
emissor de JWT de staff (`/auth/login`, valida e-mail/senha no Customer Service) e
authorizer — além dos secrets no Secrets Manager.

**Secrets necessários** (além dos já criados): `CUSTOMER_SERVICE_URL_MAIN` — a URL do
**NLB interno** do customer-service (`http://<dns-do-nlb>:8080`). O DNS
`*.svc.cluster.local` não serve: a Lambda está na VPC, mas fora do cluster. Como o customer
ainda não subiu, crie agora com um valor provisório, por exemplo `http://pendente:8080`
(o Terraform só aceita `http://` para o NLB interno, e o CD já declara isso). O valor real
entra na **FASE 8**.

**Como ligar (pipeline):**
1. Mergeie o PR da branch `docs/readme-fase4` do lambda na `main`:
   https://github.com/TechChalleng-FIAP-SOAT/workbench-lambda/pull/1
2. Ou Actions → **CD** → **Re-run all jobs**.

---

## FASE 6 — Ligar os 4 microsserviços (deploy no EKS)

**O que faz:** builda a imagem, publica no Docker Hub e aplica os manifestos
(`k8s/`) no cluster EKS, subindo os pods.

**Pré-requisito:** criar a **variável** (não secret) `USE_AWS=true` na org
(Settings → Secrets and variables → Actions → aba **Variables**). Sem ela, o job
`deploy-aws` fica *skipped*.

**Secrets usados pelos apps:** cada serviço usa a URL/credencial da **sua** instância —
`DB_URL_OS_MAIN`+`DB_USERNAME_OS`+`DB_PASSWORD_OS` (os-service),
`DB_URL_BILLING_MAIN`+`DB_USERNAME_BILLING`+`DB_PASSWORD_BILLING` (billing),
`DB_URL_CUSTOMER_MAIN`+`DB_USERNAME_CUSTOMER`+`DB_PASSWORD_CUSTOMER` (customer),
`MONGODB_URI` (execution) — além de `JWT_SECRET` (igual em todos), `MP_ACCESS_TOKEN`
(billing), `ADMIN_INITIAL_PASSWORD` (customer, no 1º deploy) e (opcional) `DD_API_KEY`.

**O que o pipeline faz sozinho em cada deploy:**
- Valida os secrets obrigatórios e para no início se faltar algum.
- Monta o Secret da app com os secrets da org, e o ConfigMap `<serviço>-runtime` com
  `DD_ENV`, `DD_VERSION` (= tag da imagem) e, nos serviços da Saga, `MESSAGING_ENABLED=true`
  e os ARNs/URLs do SNS/SQS desta conta.
- Troca o `REPLACE_IMAGE` do `app.yaml` pela imagem do commit antes do `apply` (um rollout).
- Na primeira vez, recria o Service se ele ainda for um LB público (vira NLB interno),
  e remove o Postgres de dev de deploys antigos (billing e customer).

**Observações desta entrega (paridade com o monólito):**
- **os-service**: o `NOTIFICATIONS_TOPIC_ARN` (e-mail de status ao cliente) vem do
  ConfigMap de execução; a validação de cliente/veículo e a busca do e-mail chamam o
  customer-service pelo DNS interno do cluster (`k8s/configmap.yaml`).
- **customer-service**: a migration cria o usuário staff seed `admin@workbench.dev`
  (com a senha de `ADMIN_INITIAL_PASSWORD`) — use-o no primeiro `POST /auth/login` para obter um token ADMIN.
- **execution-service**: usa **MongoDB Atlas** (gerenciado, free tier) — não há Mongo
  no cluster. Pré-requisito: criar o cluster Atlas (ver FASE 3.1) e definir o secret
  `MONGODB_URI` com a connection string `mongodb+srv://...`.

**Segurança (todos os serviços exigem JWT — defesa em profundidade):**
- Agora **os 4 serviços** validam o JWT (não só o os-service). Portanto o secret
  `JWT_SECRET` precisa chegar a **todos** eles — o mesmo valor, ≥32 chars.
- Os `k8s/secret.yaml` dos 4 serviços vêm com **placeholders `REPLACE_ME`** e **não
  são aplicados** no deploy. Em vez disso, o job `deploy-aws` de cada serviço monta o
  Secret da app (`kubectl create secret ... | kubectl apply`) com os **secrets da org**:

  | Serviço | Secret k8s recebe |
  |---|---|
  | os-service | `SPRING_DATASOURCE_URL`=`DB_URL_OS_MAIN`, `_USERNAME`=`DB_USERNAME_OS`, `_PASSWORD`=`DB_PASSWORD_OS`, `JWT_SECRET` |
  | billing | `DB_URL_BILLING_MAIN`, `DB_USERNAME_BILLING`, `DB_PASSWORD_BILLING`, `JWT_SECRET`, `MP_ACCESS_TOKEN` |
  | customer | `DB_URL_CUSTOMER_MAIN`, `DB_USERNAME_CUSTOMER`, `DB_PASSWORD_CUSTOMER`, `JWT_SECRET` |
  | execution | `MONGODB_URI`, `JWT_SECRET` |

  (`DD_API_KEY` é opcional em todos; em `develop` usa os `DB_URL_*_DEVELOP`.) Um passo
  **"Validar secrets obrigatórios"** derruba o job logo no início se algum estiver
  vazio — então crie todos **antes** de mergear. Nunca commite valor real no
  `secret.yaml`.
- **Pagamento na AWS = Mercado Pago real (sandbox).** O billing sobe com
  `PAYMENT_PROVIDER=mercadopago`: a cobrança é um link do Checkout Pro e um **job
  consulta o Mercado Pago a cada 30 s** (`/v1/payments/search?external_reference={OS}`)
  para saber se foi pago. O webhook simulado `POST /api/payments/webhook` **não existe**
  na AWS (só local, com `fake`). Para pagar no vídeo: abra o `checkoutUrl` e use um
  [cartão de teste](https://www.mercadopago.com.br/developers/pt/docs/checkout-pro/integration-test/test-cards)
  com um comprador de teste; em até ~30 s a OS vai para PAGO → ENTREGUE. O desenho completo do
  fluxo (cobrança, link por e-mail, detecção do pagamento, recusa e nova cobrança) está no README
  do `workbench-billing-service`, seção **Fluxo de pagamento**.
  Use o **usuário comprador** de teste em **janela anônima**: com uma conta real o Mercado Pago
  recusa com "uma das partes é de teste".
- Ao entrar em `PAGAMENTO_PENDENTE`, a cobrança é criada automaticamente e o **link
  de pagamento** é enviado por e-mail: ao **cliente**, se o canal SES estiver ligado (FASE 4); senão, ao endereço inscrito no tópico de notificações.

**Como ligar:** mergear as PRs `ci/sonarcloud-config` dos 4 serviços na `main`
(o push na main com `USE_AWS=true` dispara o `deploy-aws`):
- os-service, billing-service, execution-service, customer-service (PR #1 de cada).
- Mergeie também o PR #1 do `workbench-messaging` (`feat/dev-compose`): é ele que põe o
  contrato da Saga na `main`, e o CI dos serviços compara a cópia de cada um com ele.

> ⚠️ Enquanto a AWS estiver **desligada**, não mergeie nessas `main` com `USE_AWS=true`
> — o `deploy-aws` vai falhar (cluster inexistente). Para mergear sem deploy, mude a
> variável `USE_AWS` para `false` antes.

**Verificar no cluster:**
```bash
aws eks update-kubeconfig --name workbench-platform-main --region us-east-1
kubectl get pods -A
kubectl get svc -A                        # EXTERNAL-IP = DNS do NLB interno de cada serviço
kubectl get hpa,pdb,networkpolicy -A
kubectl logs -n os-service deploy/os-service | grep -i "saga\|AccessDenied" | tail
```
Sem `AccessDenied` no log, a permissão de SNS/SQS dos nós está certa.

---

## FASE 7 — Ligar o gateway (API Gateway + VPC Link)

**O que faz:** cria o API Gateway REST que expõe `/auth` (público) e roteia o
resto (protegido pelo Lambda authorizer). Lê o state do lambda.

**Secrets necessários:** nenhum além dos já criados. Os serviços têm **NLB interno**
(não ficam na internet), e o gateway chega até eles por **VPC Link**, achando cada NLB pela
tag `kubernetes.io/service-name`. Por isso esta fase precisa rodar **depois da FASE 6**
(com os 4 serviços no ar); se rodar antes, o `terraform apply` falha com "no matching LB".
Os antigos `ORIGIN_URL_MAIN` e `*_ORIGIN_URL_MAIN` não são mais usados.

**Como ligar (pipeline):** mergear a branch na `main` ou Actions → **CD** →
**Re-run all jobs**:
https://github.com/TechChalleng-FIAP-SOAT/workbench-gateway/pull/1

**Sucesso:** o último step do CD imprime o `auth endpoint`
(`https://<id>.execute-api.us-east-1.amazonaws.com/main/auth`). Guarde a base dessa URL:
é por ela que toda a API é chamada. Para achar depois:
```bash
aws apigateway get-rest-apis --region us-east-1 --query "items[?name=='workbench-gateway'].id" --output text
# URL: https://<id>.execute-api.us-east-1.amazonaws.com/main
```

---

## FASE 8 — Religar o lambda com o NLB interno do customer

**Por que:** a Lambda de login (cliente e staff) chama o customer-service pelo NLB
interno, que só passou a existir na FASE 6.

```bash
aws eks update-kubeconfig --name workbench-platform-main --region us-east-1
echo "http://$(kubectl get svc customer-service -n customer-service -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'):8080"
```
Ponha esse valor no secret `CUSTOMER_SERVICE_URL_MAIN` e rode o CD do `workbench-lambda`
de novo (Actions → **CD** → **Re-run all jobs**).

---

## ✅ Testar / Gravar o vídeo

Com tudo no ar:
- `kubectl get pods -n os-service` (e demais namespaces) — mostra os pods rodando.
- `kubectl get hpa -A` — mostra o autoscaling.
- Chamar a API via API Gateway:
  - `POST /auth/login` (staff `admin@workbench.dev` com a senha de `ADMIN_INITIAL_PASSWORD`) → token ADMIN.
  - `POST /auth` (cliente por CPF) → token CLIENT.
  - Com o token: criar OS → diagnóstico → aprovar → fluxo da Saga.
  - `POST /monitoring/all` → relatório de tempo médio (staff).
- E-mail de status chegando ao endereço inscrito no tópico de notificações.
- Dashboards do Datadog populando (com `DD_VERSION` = tag da imagem).
- Os serviços **não** respondem pela internet: só pelo gateway. Para mostrar o Swagger de
  um serviço, use `kubectl port-forward -n os-service svc/os-service 8080:8080` e abra
  `http://localhost:8080/swagger-ui.html`.
- Roteiro do vídeo, passo a passo: `ROTEIRO-VIDEO.md` (raiz do workspace).

Grave tudo numa sessão só (o relógio da cobrança está correndo).

---

## 🔴 DESLIGAR — destruir tudo (parar a cobrança)

**Ordem inversa da criação** (destrói dependentes antes das dependências). Rode
cada bloco no terminal; cada `destroy` pede confirmação (`yes`).

> ⚠️ O que mais pesa no custo: **EKS, NAT Gateway e RDS**. Garanta que os 3 sumam.

### 1. Gateway (primeiro: ele procura os NLBs dos serviços, que ainda precisam existir)
```bash
cd "$WORKBENCH_DIR/workbench-gateway/terraform"
terraform init -input=false \
  -backend-config="bucket=${TF_BUCKET}" \
  -backend-config="key=gateway/main/terraform.tfstate" \
  -backend-config="region=us-east-1" -backend-config="encrypt=true"
terraform destroy -var "environment=main" -var "lambda_state_bucket=${TF_BUCKET}"   # digite: yes
```

### 2. Apps — obrigatório (os NLBs não são do Terraform)
Os NLBs internos são criados pelos Services do Kubernetes, não pelo Terraform. Se o
cluster for destruído com eles, sobram NLBs cobrando e a VPC não é apagada.
```bash
aws eks update-kubeconfig --name workbench-platform-main --region us-east-1
kubectl delete namespace os-service billing-service customer-service execution-service
# espere os NLBs sumirem (1–3 min); deve voltar vazio:
aws elbv2 describe-load-balancers --region us-east-1 \
  --query "LoadBalancers[?Scheme=='internal'].LoadBalancerName" --output text
```

### 3. Lambda
```bash
cd "$WORKBENCH_DIR/workbench-lambda/terraform"
terraform init -input=false \
  -backend-config="bucket=${TF_BUCKET}" \
  -backend-config="key=lambda/main/terraform.tfstate" \
  -backend-config="region=us-east-1" -backend-config="encrypt=true"
# O destroy pede as variáveis obrigatórias e o jar (só para validar; nada disso é aplicado).
mkdir -p ../target && [ -f ../target/workbench-lambda.jar ] || touch ../target/workbench-lambda.jar
terraform destroy -var "environment=main" \
  -var "customer_service_url=http://pendente:8080" -var "customer_service_url_internal=true" \
  -var "jwt_secret=destroy-destroy-destroy-destroy-0000" \
  -var 'vpc_subnet_ids=["subnet-x"]' -var 'vpc_security_group_ids=["sg-x"]'   # yes
```

### 4. Messaging
```bash
cd "$WORKBENCH_DIR/workbench-messaging"
terraform init -input=false -reconfigure \
  -backend-config="bucket=${TF_BUCKET}" \
  -backend-config="key=messaging/main/terraform.tfstate" \
  -backend-config="region=us-east-1" -backend-config="encrypt=true"
terraform destroy -var "use_localstack=false" -var "environment=main"   # yes
```

### 5. Database (RDS)
```bash
cd "$WORKBENCH_DIR/workbench-database/infra/terraform"
terraform init -input=false \
  -backend-config="bucket=${TF_BUCKET}" \
  -backend-config="key=workbench-database/main/terraform.tfstate" \
  -backend-config="region=us-east-1" -backend-config="use_lockfile=true"
terraform destroy \
  -var "environment=main" -var "name_prefix=workshop" \
  -var "k8s_remote_state_bucket=${TF_BUCKET}" \
  -var 'services={os_service={db_name="os_service",db_username="os_service"},billing={db_name="billing",db_username="billing"},customer={db_name="customer",db_username="customer"}}' \
  -var 'service_passwords={os_service="<senha-os>",billing="<senha-billing>",customer="<senha-customer>"}'   # yes
```
> Remove as **3 instâncias** (os-service, billing, customer) e seus SGs/subnet groups.

> **MongoDB Atlas:** não é AWS — o `destroy` não o toca. Se quiser encerrar, pause ou
> apague o cluster no painel do Atlas (o free tier `M0` não gera custo mesmo ligado).

### 6. k8s-terraform (VPC + EKS) — por último
```bash
cd "$WORKBENCH_DIR/workbench-k8s-terraform"
terraform init -input=false \
  -backend-config="bucket=${TF_BUCKET}" \
  -backend-config="key=k8s/main/terraform.tfstate" \
  -backend-config="region=us-east-1" -backend-config="encrypt=true"
terraform destroy -var "aws_region=us-east-1" -var "environment=main"   # yes
```

### 7. Conferir que não sobrou nada cobrando
```bash
aws eks list-clusters --region us-east-1                      # deve vir vazio
aws rds describe-db-instances --region us-east-1 --query 'DBInstances[].DBInstanceIdentifier'
aws ec2 describe-nat-gateways --region us-east-1 --filter Name=state,Values=available --query 'NatGateways[].NatGatewayId'
aws ec2 describe-instances --region us-east-1 --filters Name=instance-state-name,Values=running --query 'Reservations[].Instances[].InstanceId'
aws elbv2 describe-load-balancers --region us-east-1 --query 'LoadBalancers[].LoadBalancerName'
```
Se os 5 vierem vazios, **a cobrança parou**. (O bucket S3 do state pode ficar —
custa centavos — ou apague com `aws s3 rb s3://"$TF_BUCKET" --force`.)

---

## Resumo rápido (checklist)

**Ligar:**
- [ ] 1. k8s-terraform — Actions → CD (já existe o cluster? rode de novo para criar a permissão SNS/SQS dos nós)
- [ ] 2. outputs → secrets (VPC_ID_MAIN, SUBNET_IDS_MAIN, VPC_SECURITY_GROUP_IDS_MAIN, DB_PASSWORD_OS/BILLING/CUSTOMER, DB_USERNAME_OS/BILLING/CUSTOMER = os_service/billing/customer, JWT_SECRET)
- [ ] 3. database — mergear PR na main → 3 RDS; `terraform output -json service_jdbc_urls` → criar DB_URL_OS_MAIN, DB_URL_BILLING_MAIN, DB_URL_CUSTOMER_MAIN
- [ ] 3.1 MongoDB Atlas — cluster `fiap-db-mongo` ✅; criar usuário `execution`, network access 0.0.0.0/0; criar secret MONGODB_URI
- [ ] 2b. secrets dos apps: MP_ACCESS_TOKEN, ADMIN_INITIAL_PASSWORD (e DD_API_KEY, opcional)
- [ ] 4. messaging — terraform apply (terminal) com notification_email e alert_email; confirmar os 2 e-mails
- [ ] 5. lambda — CUSTOMER_SERVICE_URL_MAIN=http://pendente:8080; mergear PR na main
- [ ] 6. apps — variable USE_AWS=true + mergear PRs dos 4 serviços (e o do messaging)
- [ ] 7. gateway — mergear PR na main (depois da 6); anotar a URL do `auth endpoint`
- [ ] 8. lambda — CUSTOMER_SERVICE_URL_MAIN = DNS do NLB interno do customer; re-run do CD

**Testar/gravar.**

**Desligar:** gateway → apps (apagar os namespaces e esperar os NLBs sumirem) → lambda → messaging → database → k8s → conferir.
