---
title: API — Monitoramento
tags:
  - api
  - monitoramento
  - analytics
aliases:
  - Monitoring API
  - Analytics
---

# API — Monitoramento

> [!info] Analytics de Desempenho
> Endpoints para análise de tempo médio de execução por tipo de serviço. Útil para planejamento de capacidade e identificação de gargalos.

## POST /monitoring/all — Tempo Médio por Tipo de Serviço

Retorna o tempo médio de execução (em minutos) para cada tipo de serviço no período informado.

**Request Body:**
```json
{
  "startDate": "2024-01-01",
  "endDate": "2024-01-31"
}
```

**Response 200:**
```json
[
  {
    "serviceTypeId": "uuid",
    "serviceTypeName": "Freios",
    "averageExecutionTimeMinutes": 120,
    "totalServices": 15
  },
  {
    "serviceTypeId": "uuid",
    "serviceTypeName": "Motor",
    "averageExecutionTimeMinutes": 240,
    "totalServices": 8
  }
]
```

---

## POST /monitoring/by-id — Tempo Médio de um Tipo Específico

Retorna o tempo médio de execução para um tipo de serviço específico.

**Request Body:**
```json
{
  "serviceTypeId": "uuid-do-tipo",
  "startDate": "2024-01-01",
  "endDate": "2024-01-31"
}
```

**Response 200:**
```json
{
  "serviceTypeId": "uuid",
  "serviceTypeName": "Freios",
  "averageExecutionTimeMinutes": 120,
  "totalServices": 15
}
```

---

## Como é Calculado

O tempo de execução de um serviço é medido entre:
- `startedAt`: quando o técnico muda o status para `DOING`
- `completedAt`: quando o técnico muda o status para `DONE`

$$
\text{tempo\_execução} = \text{completedAt} - \text{startedAt}
$$

$$
\text{média} = \frac{\sum \text{tempo\_execução}}{\text{total de serviços}}
$$

> [!warning] Serviços Incompletos
> Serviços ainda em `TO_DO` ou `DOING` não são incluídos no cálculo (sem `completedAt`).

---

## Domínio: ServiceAverageTime

```
ServiceAverageTime
├── serviceTypeId (UUID)
├── serviceTypeName (String)
├── averageExecutionTimeMinutes (Long)
└── totalServices (Integer)
```

---

## Links Relacionados
- [[API - Servicos]]
- [[Ciclo de Vida da OS]]
