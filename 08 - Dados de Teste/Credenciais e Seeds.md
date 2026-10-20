---
title: Credenciais e Dados de Teste
tags:
  - dados-teste
  - seeds
  - credenciais
aliases:
  - Test Data
  - Seeds
  - Dados Iniciais
---

# Credenciais e Dados de Teste

> [!info] Como São Carregados
> Os dados abaixo são inseridos automaticamente pelo `init.sh` na criação do banco e pelo `DataInitializer.java` na inicialização da aplicação. A inserção é **idempotente** — re-executar não duplica dados.

---

## Usuários

### Super Admin (único usuário pré-carregado)

| Campo | Valor |
|---|---|
| Email | `superadmin@system.com` |
| Senha | `coxinha123` |
| Roles | `ROLE_ADMIN` + `ROLE_USER` + `ROLE_TECHNICIAN` |

**Login via curl:**
```bash
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"superadmin@system.com","password":"coxinha123"}'
```

**Resposta:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiJ9..."
}
```

> [!danger] Não use em Produção
> Este usuário tem senha pública. Em produção, altere as credenciais ou desative este usuário.

---

## Clientes Pré-carregados

| Nome | CPF | Email | Veículos |
|---|---|---|---|
| João da Silva | 529.982.247-25 | joao@email.com | 2 |
| Maria Souza | 071.246.320-80 | maria@email.com | 1 |
| Carlos Oliveira | 187.468.800-11 | carlos@email.com | 0 |

---

## Veículos Pré-carregados

| Placa | Marca | Modelo | Ano | Dono |
|---|---|---|---|---|
| ABC-1234 | Honda | Civic | 2020 | João da Silva |
| DEF-5678 | Toyota | Corolla | 2019 | João da Silva |
| GHI-9012 | Volkswagen | Gol | 2021 | Maria Souza |

---

## Produtos Pré-carregados

### Peças (Parts)

| Nome | SKU | Preço Unitário | Tipo |
|---|---|---|---|
| Pastilha de Freio Dianteira | BRK-PAD-001 | R$ 125,00 | UNIT |

### Suprimentos (Supplies)

| Nome | SKU | Preço Unitário | Tipo |
|---|---|---|---|
| Óleo Motor 5W30 | OIL-5W30 | R$ 45,90 | LITER |

---

## Estoque Pré-carregado

| Produto | Quantidade | Qtd Mínima | Disponível |
|---|---|---|---|
| Pastilha de Freio (BRK-PAD-001) | 100 | 10 | 100 |

---

## Tipos de Serviço Pré-carregados

| Nome | Descrição |
|---|---|
| Freios | Verificação e troca de componentes de freio |
| Motor | Manutenção e reparo do motor |
| Suspensão | Amortecedores, molas, alinhamento |
| Elétrica | Sistema elétrico e eletrônico |
| Revisão | Revisão geral preventiva |

---

## Fluxo de Teste Rápido

Copie e execute sequencialmente para testar o fluxo completo:

```bash
# 1. Login
TOKEN=$(curl -s -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"superadmin@system.com","password":"coxinha123"}' \
  | jq -r '.token')

# 2. Listar clientes
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/api/clients | jq

# 3. Criar OS para João (ABC-1234)
# Obter IDs primeiro:
CLIENT_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/api/clients/cpf/52998224725 | jq -r '.id')

VEHICLE_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/api/vehicles/plate/ABC-1234 | jq -r '.id')

SERVICE_TYPE_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/service-types | jq -r '.[0].id')

# Criar OS
OS_ID=$(curl -s -X POST http://localhost:8080/order \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"vehicleId\": \"$VEHICLE_ID\",
    \"clientId\": \"$CLIENT_ID\",
    \"description\": \"Barulho no freio dianteiro\",
    \"services\": [{
      \"serviceTypeId\": \"$SERVICE_TYPE_ID\",
      \"description\": \"Verificar e trocar pastilhas\"
    }]
  }" | jq -r '.id')

echo "OS criada: $OS_ID"
```

---

## Script de Validação Completo

Para executar o fluxo completo automatizado:

```bash
chmod +x validation.sh
./validation.sh
```

O script cobre: criação → diagnóstico → reserva → aprovação → execução → finalização → entrega.

---

## Links Relacionados
- [[Quickstart]]
- [[API - Autenticacao]]
- [[API - Clientes]]
- [[Ciclo de Vida da OS]]
- [[Autorizacao e Roles]]
