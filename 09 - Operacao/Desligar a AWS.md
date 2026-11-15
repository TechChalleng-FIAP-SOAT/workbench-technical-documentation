---
title: Desligar a AWS
tags:
  - operacao
  - aws
  - custo
aliases:
  - TEARDOWN-AWS
---

# 🔴 DESLIGAR TUDO NA AWS (parar a cobrança)

> [!info] Antes dos comandos
> Os comandos usam duas variáveis do seu terminal. Defina uma vez por sessão:
> ```bash
> export WORKBENCH_DIR="<pasta onde estão os 11 repositórios workbench-*>"
> export TF_BUCKET="workbench-tfstate-<ID-da-conta-AWS>"   # bucket do state do Terraform
> ```

Guia rápido e autossuficiente para **destruir toda a infra** quando parar de mexer.
Enquanto houver recursos no ar, a AWS cobra (~**US$ 5–8/dia** com tudo ligado). Rode
isto ao fim de cada sessão.

> **O que cobra de verdade:** EKS (control plane), NAT Gateway, instâncias EC2 (nós do
> EKS) e RDS. O objetivo é zerar os 4. Commits/PRs **não** cobram nada — só os recursos
> criados pelo `terraform apply`.

> **MongoDB Atlas** não é AWS e o free tier `M0` **não gera custo** mesmo ligado. Não
> precisa desligar; se quiser, apague o cluster no painel do Atlas (https://cloud.mongodb.com).

---

## ⚡ TL;DR — a conferência que importa

Se você quer só saber "estou sendo cobrado agora?", rode o **Passo 7** primeiro. Se os
5 comandos vierem vazios, não há cobrança de compute/RDS. Se vier algo, siga os passos
1→6 para destruir.

---

## Pré-requisitos

- AWS CLI autenticado na mesma conta/região do deploy (`us-east-1`).
- `terraform` instalado.
- A senha que você usou no RDS (para o passo 5). Se não lembrar, veja a nota no fim.
- Bucket de state: `workbench-tfstate-<ID-da-conta>` (ajuste se o seu for outro).

```bash
BASE="$WORKBENCH_DIR"
BUCKET="$TF_BUCKET"
REGION="us-east-1"
```

---

## Ordem de destruição (inversa da criação)

Dependentes primeiro, base por último. Cada `destroy` pede confirmação — digite `yes`.

### 1. Gateway (API Gateway) — primeiro
Ele procura os NLBs internos dos serviços pela tag; eles ainda precisam existir.
```bash
cd "$BASE/workbench-gateway/terraform"
terraform init -input=false \
  -backend-config="bucket=$BUCKET" \
  -backend-config="key=gateway/main/terraform.tfstate" \
  -backend-config="region=$REGION" -backend-config="encrypt=true"
terraform destroy -var "environment=main" -var "lambda_state_bucket=$BUCKET"   # yes
```

### 2. Apps (Kubernetes) — obrigatório
Os NLBs internos são criados pelos Services do Kubernetes, **não pelo Terraform**. Se o
cluster for destruído com eles, sobram NLBs cobrando e a VPC não é apagada.
```bash
aws eks update-kubeconfig --name workbench-platform-main --region "$REGION"
kubectl delete namespace os-service billing-service customer-service execution-service
# espere os NLBs sumirem (1–3 min); deve voltar vazio:
aws elbv2 describe-load-balancers --region "$REGION" \
  --query "LoadBalancers[?Scheme=='internal'].LoadBalancerName" --output text
```

### 3. Lambda (auth)
```bash
cd "$BASE/workbench-lambda/terraform"
terraform init -input=false \
  -backend-config="bucket=$BUCKET" \
  -backend-config="key=lambda/main/terraform.tfstate" \
  -backend-config="region=$REGION" -backend-config="encrypt=true"
# O destroy pede as variáveis obrigatórias e o jar (só para validar; nada disso é aplicado).
mkdir -p ../target && [ -f ../target/workbench-lambda.jar ] || touch ../target/workbench-lambda.jar
terraform destroy -var "environment=main" \
  -var "customer_service_url=http://pendente:8080" -var "customer_service_url_internal=true" \
  -var "jwt_secret=destroy-destroy-destroy-destroy-0000" \
  -var 'vpc_subnet_ids=["subnet-x"]' -var 'vpc_security_group_ids=["sg-x"]'   # yes
```

### 4. Messaging (SNS/SQS)
```bash
cd "$BASE/workbench-messaging"
terraform init -input=false -reconfigure \
  -backend-config="bucket=$BUCKET" \
  -backend-config="key=messaging/main/terraform.tfstate" \
  -backend-config="region=$REGION" -backend-config="encrypt=true"
terraform destroy -var "use_localstack=false" -var "environment=main"   # yes
```

### 5. Database (3 instâncias RDS)
```bash
cd "$BASE/workbench-database/infra/terraform"
terraform init -input=false \
  -backend-config="bucket=$BUCKET" \
  -backend-config="key=workbench-database/main/terraform.tfstate" \
  -backend-config="region=$REGION" -backend-config="use_lockfile=true"
terraform destroy \
  -var "environment=main" -var "name_prefix=workshop" \
  -var "k8s_remote_state_bucket=$BUCKET" \
  -var 'services={os_service={db_name="os_service",db_username="os_service"},billing={db_name="billing",db_username="billing"},customer={db_name="customer",db_username="customer"}}' \
  -var 'service_passwords={os_service="<senha-os>",billing="<senha-billing>",customer="<senha-customer>"}'   # yes
```
> Remove as 3 instâncias (os-service, billing, customer) + SGs + subnet groups.
> As senhas podem ser qualquer valor não-vazio aqui: no `destroy` elas não são
> aplicadas, só precisam satisfazer a validação da variável.

### 6. k8s-terraform (VPC + EKS) — POR ÚLTIMO
```bash
cd "$BASE/workbench-k8s-terraform"
terraform init -input=false \
  -backend-config="bucket=$BUCKET" \
  -backend-config="key=k8s/main/terraform.tfstate" \
  -backend-config="region=$REGION" -backend-config="encrypt=true"
terraform destroy -var "aws_region=$REGION" -var "environment=main"   # yes
```

### 7. ✅ Conferir que não sobrou NADA cobrando
```bash
aws eks list-clusters --region "$REGION"                      # deve vir vazio
aws rds describe-db-instances --region "$REGION" \
  --query 'DBInstances[].DBInstanceIdentifier'                # deve vir vazio
aws ec2 describe-nat-gateways --region "$REGION" \
  --filter Name=state,Values=available \
  --query 'NatGateways[].NatGatewayId'                        # deve vir vazio
aws ec2 describe-instances --region "$REGION" \
  --filters Name=instance-state-name,Values=running \
  --query 'Reservations[].Instances[].InstanceId'            # deve vir vazio
aws elbv2 describe-load-balancers --region "$REGION" \
  --query 'LoadBalancers[].LoadBalancerName'                 # deve vir vazio
```
**Se os 4 vierem vazios, a cobrança de compute/RDS parou.**

---

## O que pode ficar (custo desprezível ou zero)

- **Bucket S3 do state** (`workbench-tfstate-<ID-da-conta>`): custa centavos/mês;
  mantenha-o (é a memória do Terraform). Só apague se for abandonar o projeto:
  `aws s3 rb s3://"$TF_BUCKET" --force`.
- **MongoDB Atlas M0:** free, pode deixar ligado.
- **ECR / imagens no Docker Hub:** não cobram relevante.

---

## Problemas comuns no destroy

- **RDS "cannot delete, has dependencies":** rode o passo 5 de novo; às vezes o SG
  demora a liberar. Se travar, confira se não há snapshot segurando.
- **VPC não destrói (DependencyViolation):** quase sempre é o passo 6 rodado antes de
  algum recurso na VPC sumir (ex.: LoadBalancer de um Service k8s que ficou órfão).
  Apague os namespaces dos serviços (passo 2), espere os NLBs sumirem e rode o passo 6 de novo.
- **Esqueci a senha do RDS (passo 5):** no `destroy` a senha não é usada de fato; passe
  qualquer valor não-vazio nas 3 (ex.: `"x"`), só para satisfazer a validação.
- **`terraform destroy` pede variáveis que não tenho:** os valores de rede
  (`vpc_id`/`subnet_ids`) são resolvidos pelo `k8s_remote_state_bucket` — por isso o
  passo 5 passa o bucket em vez de VPC/subnets.

---

## Resumo

```
gateway → apps (namespaces/NLBs) → lambda → messaging → database(3 RDS) → k8s(VPC+EKS) → conferir (passo 7)
```
Atlas é à parte (free, opcional). Se o passo 7 vier tudo vazio, você não está mais
sendo cobrado.
