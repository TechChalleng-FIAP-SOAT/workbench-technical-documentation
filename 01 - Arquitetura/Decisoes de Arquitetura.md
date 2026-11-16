---
title: Decisões de Arquitetura
tags:
  - arquitetura
  - decisoes
  - adr
aliases:
  - Por que
  - Justificativas
---

# Decisões de Arquitetura

> [!abstract] Para que serve
> Uma resposta curta para cada "por que vocês escolheram isso?", com o motivo, o que se
> perdeu na troca e onde está a decisão completa (ADR ou RFC em
> `workbench-monolith/docs`). As ADRs registram a decisão; esta nota é o índice em
> perguntas.

---

## Bancos de dados

### Por que PostgreSQL no os-service, no billing e no customer?
Os três têm dados **relacionais** com regras que o banco precisa garantir:
- **customer:** veículo sempre pertence a um cliente (chave estrangeira); CPF/CNPJ, placa e
  e-mail do usuário da equipe são únicos.
- **billing:** dinheiro. Orçamento, itens, pagamento e histórico precisam de transação ACID,
  `NUMERIC` exato e unicidade (um pagamento por OS; a trava `SELECT ... FOR UPDATE` evita
  cobrança dupla).
- **os-service:** máquina de estados da OS e estado da Saga, com trava otimista
  (`version`) para duas decisões simultâneas não gravarem as duas.

O PostgreSQL já era o banco das Fases 1–3 ([RFC-0002](https://github.com/TechChalleng-FIAP-SOAT/workbench-monolith/blob/main/docs/rfc/RFC-0002-escolha-banco-dados.md)),
tem `JSONB`, roda gerenciado no RDS e cada schema é versionado por **Flyway**.
**Troca:** três instâncias para operar. **Decisão:** RFC-0002 + [ADR-0006](https://github.com/TechChalleng-FIAP-SOAT/workbench-monolith/blob/main/docs/adr/ADR-0006-arquitetura-microsservicos-fase4.md).

### Por que MongoDB no execution-service?
- O PDF exige **ao menos um banco NoSQL**, e o execution é o melhor candidato: catálogo de
  produtos (peças e insumos com atributos diferentes), estoque, reservas e movimentos são
  **documentos lidos e gravados por produto ou por OS**, sem junções com dados de outros
  serviços.
- A reserva é "tudo ou nada" (ajusta o estoque, grava a reserva e o movimento). O MongoDB
  faz isso com **transação multidocumento** (`MongoTransactionManager`, replica set), e duas
  reservas simultâneas no mesmo estoque abortam uma delas (*WriteConflict*) em vez de
  perder atualização.
- **Um serviço, um banco:** o execution usa só o Mongo, sem um Postgres ao lado.
Quantidades e preços são gravados como **`Decimal128`** (decimal exato do MongoDB), então
"estoque abaixo do mínimo" é uma consulta no banco. Documentos antigos, gravados como texto,
são convertidos no start (`DecimalStorageMigration`). **Decisão:** [ADR-0005](https://github.com/TechChalleng-FIAP-SOAT/workbench-monolith/blob/main/docs/adr/ADR-0005-fluxo-os-estoque-pagamento.md).

### Por que MongoDB Atlas e não DocumentDB ou Mongo no cluster?
O **Atlas M0** é gerenciado e gratuito; o Amazon DocumentDB não tem plano gratuito e cobra
por instância. Um Mongo dentro do EKS exigiria volume persistente, backup e replica set
operados por nós. **Troca:** o Atlas é criado no painel (sem Terraform) e fica fora da VPC
(acesso por usuário e senha).

### Por que uma instância RDS por serviço, e não uma com vários bancos?
O PDF pede banco próprio por serviço e que nenhum serviço acesse o de outro. Instâncias
separadas deixam isso garantido pela rede e pelas credenciais (cada instância tem o seu
security group e o seu usuário), e não só por convenção. **Troca:** custo de 3
`db.t3.micro`. **Decisão:** ADR-0006 e README do `workbench-database`.

---

## Arquitetura

### Por que 4 microsserviços e esses cortes?
Os cortes são os **bounded contexts** do DDD (Event Storming): cliente e veículo
(customer), ordem de serviço e Saga (os), orçamento e pagamento (billing), estoque e
execução (execution). Cliente e veículo ficaram juntos porque veículo não existe sem dono.
**Decisão:** ADR-0006.

### Por que arquitetura hexagonal?
O domínio (regras da OS, do estoque e do pagamento) não depende de banco, web nem
mensageria: trocar o Mercado Pago pelo pagamento simulado, ou o SNS por um adaptador
local, não mexe na regra. Cada caso de uso é uma classe. **Decisão:**
[ADR-0004](https://github.com/TechChalleng-FIAP-SOAT/workbench-monolith/blob/main/docs/adr/ADR-0004-arquitetura-hexagonal.md).

### Por que Saga orquestrada e não coreografada?
Existe uma **pausa humana** (o cliente aprova o orçamento) e compensações diferentes
conforme o ponto da falha. Com um orquestrador (o os-service), o estado da Saga fica num
lugar só, visível por `GET /order/{id}/saga`, e a compensação é decidida em um ponto.
**Troca:** o os-service conhece todos os passos. **Decisão:** ADR-0006 e
[[Arquitetura e Saga - Visao Completa V2]].

### Como a Saga aguenta mensagem repetida, atrasada ou simultânea?
Cada evento só é aceito no passo esperado; cada rodada tem `sagaId` próprio; o estado tem
trava otimista; os comandos saem depois do commit; os participantes são idempotentes; um
job reenvia comando sem resposta. **Decisão:**
[ADR-0008](https://github.com/TechChalleng-FIAP-SOAT/workbench-monolith/blob/main/docs/adr/ADR-0008-robustez-da-saga.md).

### Por que SNS + SQS e não Kafka ou RabbitMQ?
Gerenciados pela AWS, sem broker para operar, com **DLQ** por fila e custo por uso. O SNS
faz o *fan-out* (um tópico por serviço emissor) e o SQS garante a entrega a cada
consumidor. **Troca:** entrega "pelo menos uma vez" e sem ordem garantida — tratado pela
Saga (pergunta anterior). **Decisão:** ADR-0006.

### Por que REST entre os-service e customer-service?
Validar cliente e veículo ao abrir a OS precisa da resposta **na hora** (a OS não pode
nascer para um cliente que não existe). O resto do fluxo é assíncrono. O os-service tem
timeout e devolve 503 se o customer estiver fora. **Decisão:**
[ADR-0001](https://github.com/TechChalleng-FIAP-SOAT/workbench-monolith/blob/main/docs/adr/ADR-0001-padrao-comunicacao.md) e ADR-0006.

### Por que o pagamento é confirmado por consulta, e não por webhook?
Um webhook exigiria um endpoint público para o Mercado Pago. Com a consulta a cada 30 s
(`ShedLock` garante uma réplica por vez), nenhum endpoint de pagamento fica na internet.
**Troca:** até ~30 s de atraso. **Decisão:** ADR-0008. O webhook simulado do billing só existe com
`PAYMENT_PROVIDER=fake`, que o serviço só aceita no perfil `local` (`FakeProviderGuard`).

---

## Infraestrutura e segurança

### Por que EKS (Kubernetes) e não ECS ou Elastic Beanstalk?
O PDF pede Kubernetes com HPA. O EKS é o Kubernetes gerenciado da AWS; manifestos, HPA e
probes funcionam igual ao cluster local. **Decisão:**
[RFC-0001](https://github.com/TechChalleng-FIAP-SOAT/workbench-monolith/blob/main/docs/rfc/RFC-0001-escolha-provedor-nuvem.md) e
[ADR-0002](https://github.com/TechChalleng-FIAP-SOAT/workbench-monolith/blob/main/docs/adr/ADR-0002-uso-hpa.md).

### Por que API Gateway + Lambda na autenticação?
O PDF pede um gateway e uma função serverless que valide o CPF e emita o token. A Lambda
emite o JWT (cliente por CPF, staff por e-mail e senha) e o authorizer valida o token antes
de qualquer rota protegida. **Decisão:**
[RFC-0003](https://github.com/TechChalleng-FIAP-SOAT/workbench-monolith/blob/main/docs/rfc/RFC-0003-estrategia-autenticacao.md).

### Por que JWT RS256 (assimétrico) e não HS256?
Com HS256 o mesmo segredo assina e verifica: os 4 serviços, a Lambda e o authorizer tinham o
segredo, e qualquer um deles comprometido emitia token de ADMIN para todos. Com RS256 só a
Lambda tem a chave **privada**; os outros têm a pública e só verificam. O token de serviço do
os-service usa outro par, aceito só pelo customer. **Troca:** 4 secrets de chave em vez de
1, e trocar as chaves exige redeploy. **Decisão:**
[ADR-0009](https://github.com/TechChalleng-FIAP-SOAT/workbench-monolith/blob/main/docs/adr/ADR-0009-jwt-rs256.md).

### Por que os serviços também validam o JWT, se o gateway já valida?
Defesa em profundidade: dentro da VPC, uma chamada que não passou pelo gateway continua
precisando de token válido, e a regra de "cliente só vê os próprios dados" fica no caso de
uso de cada serviço.

### Por que os serviços não ficam na internet?
Cada um tem um **NLB interno**; o gateway chega por **VPC Link**. Só o API Gateway, com
authorizer e limite de requisições, é público. **Decisão:**
[ADR-0007](https://github.com/TechChalleng-FIAP-SOAT/workbench-monolith/blob/main/docs/adr/ADR-0007-rede-e-segredos.md).

### Por que os segredos não têm valor padrão?
Para **falhar fechado**: um deploy com variável esquecida não sobe, em vez de subir com um
segredo conhecido. Os valores de desenvolvimento ficam no perfil `local`. **Decisão:**
ADR-0007.

### Por que repositórios separados?
Cada serviço e cada camada de infraestrutura tem pipeline e ciclo de deploy próprios; uma
mudança no billing não redeploya o customer. **Decisão:**
[ADR-0003](https://github.com/TechChalleng-FIAP-SOAT/workbench-monolith/blob/main/docs/adr/ADR-0003-split-multiplos-repositorios.md).

---

## Limitações aceitas

| Limitação | Por que ficou |
|---|---|
| Reserva de estoque sem prazo | Precisa de regra de negócio (em quantos dias recusar sozinho) |
| SES em sandbox até a AWS aprovar a produção | O pedido é manual e analisado pela AWS (`scripts/ses-request-production.sh`); até lá, só destinatários verificados recebem |
| Limite de login por réplica | Contador compartilhado (Redis) só compensa com o serviço exposto em escala |
| RDS com 1 dia de backup, sem Multi-AZ | Limite do plano gratuito da AWS |

## Notas relacionadas
- [[Visao Geral]] · [[Arquitetura e Saga - Visao Completa V2]] · [[Evolucao das Fases]]
