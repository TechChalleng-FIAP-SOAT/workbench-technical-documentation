---
title: API — Peças e Suprimentos
tags:
  - api
  - produtos
  - pecas
  - suprimentos
aliases:
  - Parts
  - Supplies
  - Produtos
---

# API — Peças e Suprimentos

> [!info] Dois Tipos de Produto
> **Peças (Parts):** componentes físicos instalados no veículo (ex: pastilha de freio).
> **Suprimentos (Supplies):** insumos consumíveis (ex: óleo, fluidos). Suportam unidades fracionadas.

## Peças — `/api/parts`

### POST /api/parts — Criar Peça

**Request Body:**
```json
{
  "name": "Pastilha de Freio Dianteira",
  "sku": "BRK-PAD-001",
  "description": "Pastilha para freio a disco",
  "unitPrice": 125.00,
  "unit": "UNIT"
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "name": "Pastilha de Freio Dianteira",
  "sku": "BRK-PAD-001",
  "unitPrice": 125.00,
  "unit": "UNIT",
  "active": true
}
```

---

### GET /api/parts — Listar Peças

Retorna apenas peças com `active = true`.

---

### GET /api/parts/{id} — Buscar por ID

---

### GET /api/parts/sku/{sku} — Buscar por SKU

```bash
GET /api/parts/sku/BRK-PAD-001
```

---

### PUT /api/parts/{id} — Atualizar Peça

Permite alterar nome, descrição, preço. **SKU é imutável.**

---

### DELETE /api/parts/{id} — Desativar Peça (Soft Delete)

**Response 204**

---

## Suprimentos — `/api/supplies`

### POST /api/supplies — Criar Suprimento

**Request Body:**
```json
{
  "name": "Óleo Motor 5W30",
  "sku": "OIL-5W30",
  "description": "Óleo lubrificante sintético",
  "unitPrice": 45.90,
  "unit": "LITER"
}
```

> [!tip] Unidade Fracionada
> Suprimentos suportam `unit: "LITER"`, `"ML"`, `"KG"` etc., permitindo quantidades decimais (ex: 0.5 litros).

---

### GET /api/supplies — Listar Suprimentos

---

### GET /api/supplies/{id} — Buscar por ID

---

### GET /api/supplies/sku/{sku} — Buscar por SKU

---

### PUT /api/supplies/{id} — Atualizar Suprimento

---

### DELETE /api/supplies/{id} — Desativar Suprimento (Soft Delete)

---

## Dados Pré-Carregados

| Tipo | Nome | SKU | Preço |
|---|---|---|---|
| Part | Pastilha de Freio | BRK-PAD-001 | R$ 125,00 |
| Supply | Óleo Motor 5W30 | OIL-5W30 | R$ 45,90 |

## Links Relacionados
- [[API - Estoque]]
- [[Credenciais e Seeds]]
