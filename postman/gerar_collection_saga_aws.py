#!/usr/bin/env python3
"""Gera a collection Postman do E2E da Saga na AWS (caminho feliz, falhas e monitoramento) e o environment.

Uso:   python3 gerar_collection_saga_aws.py [pasta_de_saida] [url_do_gateway]
       (padrão: a pasta deste script e o gateway abaixo)

Cada execução da collection gera CPF, placa, cliente e produto NOVOS (passo 0). Depois de recriar o
gateway (teardown + deploy), o id da API muda: gere de novo passando a nova `invoke_url`.
"""
import json, os, sys

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT, exist_ok=True)
GATEWAY = sys.argv[2] if len(sys.argv) > 2 else "https://rin3bn5vqi.execute-api.us-east-1.amazonaws.com/main"

def lines(s):
    return [l for l in s.strip("\n").split("\n")]

def event(kind, script):
    return {"listen": kind, "script": {"type": "text/javascript", "exec": lines(script)}}

def req(name, method, path, body=None, auth="inherit", pre=None, test=None, desc=""):
    r = {
        "method": method,
        "header": [{"key": "Content-Type", "value": "application/json"}] if body is not None else [],
        "url": {"raw": "{{gatewayUrl}}" + path, "host": ["{{gatewayUrl}}"], "path": [p for p in path.strip("/").split("/")]},
        "description": desc,
    }
    if body is not None:
        r["body"] = {"mode": "raw", "raw": json.dumps(body, indent=2, ensure_ascii=False),
                     "options": {"raw": {"language": "json"}}}
    if auth == "noauth":
        r["auth"] = {"type": "noauth"}
    elif auth == "client":
        r["auth"] = {"type": "bearer", "bearer": [{"key": "token", "value": "{{clientToken}}", "type": "string"}]}
    item = {"name": name, "request": r, "event": []}
    if pre:
        item["event"].append(event("prerequest", pre))
    if test:
        item["event"].append(event("test", test))
    return item

# ------------------------------------------------------------------ scripts reutilizáveis
GERA_DADOS = r"""
// Gera dados NOVOS a cada execução (CPF válido, placa, nome, e-mail, SKU) e limpa o estado anterior.
function cpf() {
  let d;
  do {
    d = []; for (let i = 0; i < 9; i++) d.push(Math.floor(Math.random() * 10));
  } while (d.every(x => x === d[0]));
  let s = 0; for (let i = 0; i < 9; i++) s += d[i] * (10 - i);
  let r = (s * 10) % 11; d.push(r >= 10 ? 0 : r);
  s = 0; for (let i = 0; i < 10; i++) s += d[i] * (11 - i);
  r = (s * 10) % 11; d.push(r >= 10 ? 0 : r);
  return d.join('');
}
const L = 'ABCDEFGHJKLMNPQRSTUVWXYZ';
const letras = () => Array.from({length: 3}, () => L[Math.floor(Math.random() * L.length)]).join('');
const sufixo = String(Date.now()).slice(-7);
const nomes = ['Joana Prado', 'Carlos Menezes', 'Luiza Andrade', 'Rafael Tavares', 'Beatriz Nogueira', 'Marcos Vilela'];
const carros = [['Fiat', 'Argo'], ['Chevrolet', 'Onix'], ['Hyundai', 'HB20'], ['Renault', 'Kwid'], ['Toyota', 'Etios']];
const cores = ['Prata', 'Preto', 'Branco', 'Vermelho', 'Azul'];
const pick = a => a[Math.floor(Math.random() * a.length)];
const carro = pick(carros);
const v = {
  cpf: cpf(),
  placa: letras() + '-' + String(Math.floor(Math.random() * 10000)).padStart(4, '0'),
  nome: pick(nomes) + ' ' + sufixo,
  email: 'saga' + sufixo + '@example.com',
  telefone: '119' + String(Math.floor(Math.random() * 100000000)).padStart(8, '0'),
  marca: carro[0], modelo: carro[1], cor: pick(cores),
  ano: 2012 + Math.floor(Math.random() * 12),
  sku: 'FILTRO-' + sufixo,
  produto: 'Filtro de ar ' + sufixo
};
Object.keys(v).forEach(k => pm.collectionVariables.set(k, v[k]));
['token', 'clientToken', 'clientId', 'productId', 'orderId', 'serviceId', 'gatewayPaymentId', 'checkoutUrl']
  .forEach(k => pm.collectionVariables.unset(k));
console.log('Dados desta execução:', JSON.stringify(v));
""".replace("\n\n", "\n")

def captura(var, expr, codes="[200, 201]"):
    return f"""
pm.test('Status ' + pm.response.code + ' esperado em {codes}', () => pm.expect({codes}).to.include(pm.response.code));
if ({codes}.includes(pm.response.code)) {{
  const v = (({expr}));
  if (v !== undefined && v !== null) pm.collectionVariables.set('{var}', v);
}}
"""

def espera_status(status, delay_ms, max_tentativas, var='orderId'):
    pre = f"setTimeout(function () {{}}, {delay_ms});  // dá tempo para a Saga/mensageria andar"
    test = f"""
const want = '{status}';
const st = pm.response.code === 200 ? pm.response.json().serviceStatus : ('HTTP ' + pm.response.code);
const key = 'tentativas_{status}_{var}';
const n = Number(pm.collectionVariables.get(key) || 0) + 1;
if (st !== want && n < {max_tentativas}) {{
  // Collection Runner: tenta de novo sozinho. Enviando um request só: reenvie em alguns segundos.
  pm.collectionVariables.set(key, n);
  console.log('OS em ' + st + ', esperando ' + want + ' (tentativa ' + n + ' de {max_tentativas})');
  try {{ pm.execution.setNextRequest(pm.info.requestName); }} catch (e) {{ postman.setNextRequest(pm.info.requestName); }}
}} else {{
  pm.collectionVariables.unset(key);
  pm.test('OS em ' + want + ' (atual: ' + st + ')', () => pm.expect(st).to.eql(want));
}}
"""
    return pre, test

# ------------------------------------------------------------------ pasta A
A = []

A.append(req("0. Login staff (gera dados novos)", "POST", "/auth/login",
    body={"email": "{{staffEmail}}", "password": "{{staffPassword}}"}, auth="noauth",
    desc="Gera CPF, placa, nome, e-mail e SKU NOVOS e faz o login da equipe. Rode a pasta sempre a partir deste passo.",
    pre=GERA_DADOS,
    test="""
pm.test('Login 200 (se 401: selecione o environment "Workbench - AWS - Saga" e preencha staffPassword)', () => pm.response.to.have.status(200));
if (pm.response.code === 200) {
  const j = pm.response.json();
  pm.collectionVariables.set('token', j.token);
  pm.test('token JWT recebido', () => pm.expect(j.token).to.be.a('string').and.not.empty);
}
"""))

A.append(req("0b. Sem token -> 401 (prova do authorizer)", "GET", "/order", auth="noauth",
    test="pm.test('Gateway recusa chamada sem token (401)', () => pm.response.to.have.status(401));"))

A.append(req("1. Criar cliente (customer-service)", "POST", "/api/clients",
    body={"name": "{{nome}}", "document": "{{cpf}}", "email": "{{email}}", "phone": "{{telefone}}"},
    test=captura("clientId", "pm.response.json().id")))

A.append(req("2. Criar veículo (customer-service)", "POST", "/api/vehicles",
    body={"clientId": "{{clientId}}", "plate": "{{placa}}", "brand": "{{marca}}", "model": "{{modelo}}",
          "year": "{{ano}}", "color": "{{cor}}", "type": "CAR"},
    test="pm.test('Veículo criado', () => pm.expect([200, 201]).to.include(pm.response.code));"))
# clientId e year precisam ser números no JSON: o Postman substitui a variável como texto, então tiramos as aspas.
A[-1]["request"]["body"]["raw"] = A[-1]["request"]["body"]["raw"].replace('"{{clientId}}"', '{{clientId}}').replace('"{{ano}}"', '{{ano}}')

A.append(req("3. Criar produto (execution-service / MongoDB)", "POST", "/api/products",
    body={"name": "{{produto}}", "sku": "{{sku}}", "type": "PART", "unit": "UNIT", "category": "Filtros",
          "brand": "Tecfil", "costPrice": 18.50, "salePrice": 39.90, "warrantyMonths": 3,
          "fractionalAllowed": False, "packageSize": 1},
    test=captura("productId", "pm.response.json().id")))

A.append(req("4. Criar estoque (50 unidades)", "POST", "/api/stocks",
    body={"productId": "{{productId}}", "quantity": 50, "minimumQuantity": 5},
    test="pm.test('Estoque criado', () => pm.expect([200, 201]).to.include(pm.response.code));"))

A.append(req("5. Login cliente por CPF (Lambda)", "POST", "/auth",
    body={"cpf": "{{cpf}}"}, auth="noauth",
    desc="O cliente precisa existir (passo 1). A resposta traz o token que o CLIENTE usa para aprovar a OS.",
    test="""
pm.test('Login do cliente 200', () => pm.response.to.have.status(200));
if (pm.response.code === 200) pm.collectionVariables.set('clientToken', pm.response.json().token);
"""))

A.append(req("6. Criar OS (os-service valida cliente e placa por REST)", "POST", "/order",
    body={"cpfCnpj": "{{cpf}}", "placaVeiculo": "{{placa}}", "serviceTypes": ["TROCA_OLEO"]},
    test=captura("orderId", "pm.response.json().id", "[201]")))

A.append(req("7. Registrar diagnóstico (dispara a Saga)", "POST", "/order/{{orderId}}/diagnosis",
    body={"parts": [{"productId": "{{productId}}", "quantity": 2}],
          "services": [{"serviceType": "TROCA_OLEO", "laborCost": 80.00, "useDefault": False}]},
    test="pm.test('Diagnóstico aceito, Saga iniciada', () => pm.expect([200, 201, 202]).to.include(pm.response.code));"))

pre8, test8 = espera_status("AGUARDANDO_APROVACAO", 12000, 6)
A.append(req("8. Aguardar AGUARDANDO_APROVACAO (espera 12 s)", "GET", "/order/id/{{orderId}}", pre=pre8, test=test8,
    desc="Reserva de estoque (execution) e orçamento (billing) acontecem por SNS/SQS. Se falhar, reenvie em alguns segundos."))

A.append(req("8a. Estado da Saga", "GET", "/order/{{orderId}}/saga",
    test="""
pm.test('Estado da Saga 200', () => pm.response.to.have.status(200));
const j = pm.response.json();
console.log('Saga:', JSON.stringify({step: j.step, failureReason: j.failureReason}));
pm.test('Sem motivo de falha', () => pm.expect(j.failureReason == null).to.be.true);
"""))

A.append(req("8b. Orçamento gerado (billing-service)", "GET", "/api/budgets/service-order/{{orderId}}",
    test="""
pm.test('Orçamento 200', () => pm.response.to.have.status(200));
const j = pm.response.json();
console.log('Orçamento:', JSON.stringify({totalParts: j.totalParts, totalLabor: j.totalLabor, totalPrice: j.totalPrice}));
pm.test('totalPrice > 0', () => pm.expect(Number(j.totalPrice)).to.be.above(0));
"""))

A.append(req("8c. Estoque reservado (execution-service)", "GET", "/api/stocks/product/{{productId}}",
    test="""
pm.test('Estoque 200', () => pm.response.to.have.status(200));
const j = pm.response.json();
console.log('Estoque:', JSON.stringify({quantity: j.quantity, reservedQuantity: j.reservedQuantity}));
pm.test('2 peças reservadas', () => pm.expect(Number(j.reservedQuantity)).to.eql(2));
"""))

A.append(req("9. Cliente aprova o orçamento (token do CLIENTE)", "POST", "/order/{{orderId}}/decision",
    body={"decision": "APPROVED"}, auth="client",
    desc="Usa o clientToken: o cliente só decide a OS do próprio CPF.",
    test="pm.test('Aprovação aceita', () => pm.expect([200, 202, 204]).to.include(pm.response.code));"))

pre9, test9 = espera_status("APROVADO", 8000, 6)
A.append(req("9a. Aguardar APROVADO (espera 8 s)", "GET", "/order/id/{{orderId}}", pre=pre9, test=test9))

A.append(req("10. Iniciar execução (EM_EXECUCAO)", "PATCH", "/order/{{orderId}}",
    body={"status": "EM_EXECUCAO"},
    test="pm.test('OS em execução (204)', () => pm.expect([200, 204]).to.include(pm.response.code));"))

A.append(req("11. Listar serviços da OS (captura serviceId)", "GET", "/order/{{orderId}}/services",
    test="""
pm.test('Serviços 200', () => pm.response.to.have.status(200));
const l = pm.response.json();
pm.test('OS tem 1 serviço', () => pm.expect(l).to.be.an('array').with.lengthOf(1));
if (l.length) pm.collectionVariables.set('serviceId', l[0].id);
"""))

A.append(req("11a. Serviço em andamento (TO_DO -> DOING)", "PATCH", "/order/{{orderId}}/services/{{serviceId}}/status",
    body={"status": "DOING"}, test="pm.test('Serviço em DOING', () => pm.response.to.have.status(200));"))

A.append(req("11b. Serviço concluído (DOING -> DONE; o último DONE finaliza a OS)", "PATCH",
    "/order/{{orderId}}/services/{{serviceId}}/status",
    body={"status": "DONE"}, test="pm.test('Serviço em DONE', () => pm.response.to.have.status(200));"))

A.append(req("12. Marcar pagamento pendente (dispara a cobrança)", "PATCH", "/order/{{orderId}}",
    body={"status": "PAGAMENTO_PENDENTE"},
    test="pm.test('OS em pagamento pendente (204)', () => pm.expect([200, 204]).to.include(pm.response.code));"))

A.append(req("13. Buscar cobrança e link do Mercado Pago (espera 10 s)", "GET", "/api/payments/service-order/{{orderId}}",
    pre="setTimeout(function () {}, 10000);  // o billing cria a preferência no Mercado Pago pela fila",
    desc="Copie o checkoutUrl (variável da collection e Console) e pague com o COMPRADOR DE TESTE do Mercado Pago.",
    test="""
pm.test('Cobrança 200 (se 404: reenvie em alguns segundos)', () => pm.response.to.have.status(200));
if (pm.response.code === 200) {
  const j = pm.response.json();
  pm.collectionVariables.set('gatewayPaymentId', j.gatewayPaymentId);
  pm.collectionVariables.set('checkoutUrl', j.checkoutUrl);
  pm.test('checkoutUrl do Mercado Pago', () => pm.expect(j.checkoutUrl).to.match(/mercado/i));
  console.log('>>> PAGUE AQUI: ' + j.checkoutUrl);
}
"""))

# ------------------------------------------------------------------ pasta B
B = []
pre15, test15 = espera_status("ENTREGUE", 15000, 8)
B.append(req("14. Aguardar ENTREGUE (o job consulta o Mercado Pago a cada 30 s)", "GET", "/order/id/{{orderId}}",
    pre=pre15, test=test15,
    desc="Rode DEPOIS de pagar no checkoutUrl. No Runner tenta até 8 vezes (15 s cada); avulso, reenvie."))
B.append(req("15. Histórico do pagamento", "GET", "/api/payments/service-order/{{orderId}}/history",
    test="""
pm.test('Histórico 200', () => pm.response.to.have.status(200));
console.log('Histórico:', pm.response.text().slice(0, 500));
"""))
B.append(req("16. Estado final da Saga", "GET", "/order/{{orderId}}/saga",
    test="""
pm.test('Saga 200', () => pm.response.to.have.status(200));
console.log('Saga final:', pm.response.text().slice(0, 500));
"""))


# ------------------------------------------------------------------ pasta C (falhas e compensação)
C = []
C.append(req("C1. Nova OS para o cenário de recusa", "POST", "/order",
    body={"cpfCnpj": "{{cpf}}", "placaVeiculo": "{{placa}}", "serviceTypes": ["TROCA_OLEO"]},
    desc="Rode depois da pasta A (usa o mesmo cliente, veículo e produto).",
    test=captura("orderIdRecusa", "pm.response.json().id", "[201]")))
C.append(req("C2. Diagnóstico com 3 peças (reserva 3 no estoque)", "POST", "/order/{{orderIdRecusa}}/diagnosis",
    body={"parts": [{"productId": "{{productId}}", "quantity": 3}], "services": []},
    test="pm.test('Diagnóstico aceito', () => pm.expect([200, 201, 202]).to.include(pm.response.code));"))
preC3, testC3 = espera_status("AGUARDANDO_APROVACAO", 12000, 6, "orderIdRecusa")
C.append(req("C3. Aguardar AGUARDANDO_APROVACAO (espera 12 s)", "GET", "/order/id/{{orderIdRecusa}}", pre=preC3, test=testC3))
C.append(req("C4. Estoque com 3 peças reservadas", "GET", "/api/stocks/product/{{productId}}",
    test="""
pm.test('Estoque 200', () => pm.response.to.have.status(200));
const j = pm.response.json();
console.log('Estoque antes da recusa:', JSON.stringify({quantity: j.quantity, reservedQuantity: j.reservedQuantity}));
pm.test('3 peças reservadas', () => pm.expect(Number(j.reservedQuantity)).to.eql(3));
"""))
C.append(req("C5. Cliente RECUSA o orçamento (token do cliente)", "POST", "/order/{{orderIdRecusa}}/decision",
    body={"decision": "REJECTED", "reason": "Valor acima do esperado"}, auth="client",
    test="pm.test('Recusa aceita', () => pm.expect([200, 202, 204]).to.include(pm.response.code));"))
preC6, testC6 = espera_status("RECUSADA", 10000, 6, "orderIdRecusa")
C.append(req("C6. Aguardar RECUSADA (espera 10 s)", "GET", "/order/id/{{orderIdRecusa}}", pre=preC6, test=testC6))
C.append(req("C7. COMPENSAÇÃO: reserva liberada (reservedQuantity volta a 0)", "GET", "/api/stocks/product/{{productId}}",
    pre="setTimeout(function () {}, 4000);",
    test="""
pm.test('Estoque 200', () => pm.response.to.have.status(200));
const j = pm.response.json();
console.log('Estoque depois da compensação:', JSON.stringify({quantity: j.quantity, reservedQuantity: j.reservedQuantity}));
pm.test('reserva liberada (0)', () => pm.expect(Number(j.reservedQuantity)).to.eql(0));
"""))
C.append(req("C8. Estado da Saga após a recusa", "GET", "/order/{{orderIdRecusa}}/saga",
    test="""
pm.test('Saga 200', () => pm.response.to.have.status(200));
const j = pm.response.json();
console.log('Saga após a recusa:', JSON.stringify({step: j.step, failureReason: j.failureReason}));
"""))
C.append(req("C9. Nova OS para o cenário sem estoque", "POST", "/order",
    body={"cpfCnpj": "{{cpf}}", "placaVeiculo": "{{placa}}", "serviceTypes": ["TROCA_OLEO"]},
    test=captura("orderIdSemEstoque", "pm.response.json().id", "[201]")))
C.append(req("C10. Diagnóstico pedindo 999 peças (só há 50)", "POST", "/order/{{orderIdSemEstoque}}/diagnosis",
    body={"parts": [{"productId": "{{productId}}", "quantity": 999}], "services": []},
    test="pm.test('Diagnóstico aceito, a Saga vai falhar na reserva', () => pm.expect([200, 201, 202]).to.include(pm.response.code));"))
C.append(req("C11. Estado da Saga sem estoque (espera 15 s)", "GET", "/order/{{orderIdSemEstoque}}/saga",
    pre="setTimeout(function () {}, 15000);",
    test="""
pm.test('Saga 200', () => pm.response.to.have.status(200));
const j = pm.response.json();
console.log('Saga sem estoque:', JSON.stringify({step: j.step, failureReason: j.failureReason}));
pm.test('Saga registra o motivo da falha', () => pm.expect(j.failureReason).to.be.a('string').and.not.empty);
"""))
C.append(req("C12. Estoque intacto (nada ficou preso)", "GET", "/api/stocks/product/{{productId}}",
    test="""
pm.test('Estoque 200', () => pm.response.to.have.status(200));
const j = pm.response.json();
pm.test('nenhuma peça reservada', () => pm.expect(Number(j.reservedQuantity)).to.eql(0));
"""))

D = [req("D1. Tempo médio por tipo de serviço (monitoring)", "POST", "/monitoring/all",
    body={"timeUnit": "MINUTES"},
    test="""
pm.test('Monitoring 200', () => pm.response.to.have.status(200));
console.log('Monitoring:', pm.response.text().slice(0, 400));
""")]

collection = {
    "info": {
        "name": "Workbench - Saga feliz E2E (AWS, dados novos)",
        "description": ("E2E da Saga orquestrada (caminho feliz) pelo API Gateway da AWS. Cada execução gera CPF, placa, "
                       "cliente e produto novos (passo 0). Pasta A: do login até o link de pagamento. Pasta B: depois de pagar "
                       "no Mercado Pago, confirma ENTREGUE. Pasta C: recusa do orçamento (compensação) e falta de estoque. Use com o environment 'Workbench - AWS - Saga'."),
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
    },
    "auth": {"type": "bearer", "bearer": [{"key": "token", "value": "{{token}}", "type": "string"}]},
    "variable": [
        {"key": "gatewayUrl", "value": GATEWAY, "description": "Padrão: API Gateway da AWS (o environment sobrescreve)."},
        {"key": "staffEmail", "value": "admin@workbench.dev"}
    ],
    "item": [
        {"name": "A. Saga feliz: do login até a cobrança", "item": A},
        {"name": "B. Depois de pagar no Mercado Pago", "item": B},
        {"name": "C. Falhas e compensação (rode depois da A)", "item": C},
        {"name": "D. Monitoramento", "item": D}
    ]
}

environment = {
    "id": "workbench-aws-saga-env",
    "name": "Workbench - AWS - Saga",
    "values": [
        {"key": "gatewayUrl", "value": GATEWAY, "type": "default", "enabled": True},
        {"key": "staffEmail", "value": "admin@workbench.dev", "type": "default", "enabled": True},
        {"key": "staffPassword", "value": "", "type": "secret", "enabled": True},
    ],
    "_postman_variable_scope": "environment"
}

with open(os.path.join(OUT, "workbench-saga-feliz-aws.postman_collection.json"), "w", encoding="utf-8") as f:
    json.dump(collection, f, indent=2, ensure_ascii=False)
with open(os.path.join(OUT, "workbench-aws-saga.postman_environment.json"), "w", encoding="utf-8") as f:
    json.dump(environment, f, indent=2, ensure_ascii=False)
print("ok", len(A) + len(B), "requests")
