# Collections Postman — Plataforma Workbench (Fase 4)

Collections para exercitar a API dos microsserviços. Cada microsserviço tem a sua
collection no próprio repositório, em `postman/`; aqui fica a **collection unificada**
(todos os serviços + o fluxo Saga ponta a ponta).

## Arquivos

| Collection | Onde | Conteúdo |
|---|---|---|
| OS Service | `workbench-os-service/postman/` | Ordem de serviço, diagnóstico, decisão do orçamento |
| Billing Service | `workbench-billing-service/postman/` | Orçamento, pagamento, webhook |
| Execution Service | `workbench-execution-service/postman/` | Produtos, estoque e reservas |
| Customer Service | `workbench-customer-service/postman/` | Clientes e veículos |
| **Plataforma (todos)** | `workbench-technical-documentation/postman/` | Os 4 serviços + pasta "Fluxo Saga (E2E)" |

## Importar

No Postman: **Import** → selecione o arquivo `*.postman_collection.json`. (Também
funciona no Insomnia e no Bruno, que importam o formato Postman v2.1.)

## Variáveis

As collections usam variáveis de collection (edite em **Variables**):

- `token` — JWT (HS256) com role `ADMIN` ou `TECHNICIAN`. Os microsserviços **não
  emitem** token (isso é da Lambda de auth); em dev, gere um token assinado com o
  `JWT_SECRET` compartilhado e cole aqui.
- `baseUrl` (nas collections por serviço) — default `http://localhost:8080`.
- `customerUrl`, `osUrl`, `billingUrl`, `executionUrl` (na collection unificada) —
  um host/porta por serviço, pois no cluster cada serviço é exposto separadamente
  (ou via `kubectl port-forward` em portas distintas localmente).

### Gerar um token de dev (JWT HS256)

Com o `JWT_SECRET` de desenvolvimento, gere um token de ADMIN (válido 24h):

```bash
python3 - <<'PY'
import hmac, hashlib, base64, json, time
def b64(b): return base64.urlsafe_b64encode(b).rstrip(b'=').decode()
secret = "SEU_JWT_SECRET_DE_DEV"
now = int(time.time())
header = {"alg":"HS256","typ":"JWT"}
payload = {"sub":"admin@workbench.dev","roles":["ADMIN"],"iat":now,"exp":now+86400}
seg = b64(json.dumps(header,separators=(',',':')).encode())+"."+b64(json.dumps(payload,separators=(',',':')).encode())
sig = hmac.new(secret.encode(), seg.encode(), hashlib.sha256).digest()
print(seg+"."+b64(sig))
PY
```

Cole o resultado na variável `token`.

## Fluxo Saga (E2E)

A pasta **"Fluxo Saga (E2E - caminho feliz)"** na collection unificada executa, em
ordem: criar cliente → veículo → OS → diagnóstico (dispara a Saga) → consultar
orçamento → aprovar → webhook de pagamento → conferir OS em PAGO/ENTREGUE. O
`orderId` é capturado automaticamente na criação da OS. Requer os 4 serviços no ar
e a mensageria (LocalStack) ativa — ver `workbench-messaging/docker-compose.dev.yml`.
