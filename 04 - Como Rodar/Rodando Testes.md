---
title: Rodando Testes
tags:
  - como-rodar
  - testes
  - jacoco
  - testcontainers
aliases:
  - Testes
  - Test Suite
---

# Rodando Testes

## Tipos de Teste

| Tipo | Nomenclatura | Executado por | Requisito |
|---|---|---|---|
| Unitário | `*Test.java` | Maven Surefire | Nenhum |
| Integração | `*IT.java` | Maven Failsafe | Docker (Testcontainers) |

---

## Comandos

### Apenas Testes Unitários
```bash
./mvnw clean package
# ou
./mvnw test
```

Não requer Docker. Executa apenas os arquivos `*Test.java`.

---

### Testes Unitários + Integração
```bash
./mvnw clean verify
```

Requer Docker. O Testcontainers sobe automaticamente um container PostgreSQL 16 para os testes de integração.

---

### Apenas Testes de Integração
```bash
./mvnw failsafe:integration-test failsafe:verify
```

---

### Relatório de Cobertura (JaCoCo)
```bash
./mvnw test jacoco:report
```

Relatório disponível em:
```
target/site/jacoco/index.html
```

Abra no browser para ver cobertura por classe, método e linha.

---

### Análise SonarQube com Cobertura
```bash
# Gerar cobertura + enviar para Sonar
./mvnw clean verify sonar:sonar
```

O JaCoCo gera `target/site/jacoco/jacoco.xml`, que o SonarQube lê automaticamente (configurado no `pom.xml`).

---

## O que é Testado

### Testes de Integração (Testcontainers)
- Mapeamentos JPA das entidades
- Conversores customizados (`ListToJsonConverter`, `ServiceStatusConverter`)
- Queries do Spring Data (JPQL + derived queries)
- Constraints do banco (unique, not-null, foreign keys)
- Persistência de enums (`@Enumerated`)

### Configuração do Banco de Teste

`src/test/resources/application-integration.yml`:
```yaml
spring:
  datasource:
    url: jdbc:tc:postgresql:16:///workshop  # Testcontainers URL especial
  jpa:
    hibernate:
      ddl-auto: create-drop                 # Recria schema a cada teste
```

> [!info] Testcontainers URL
> `jdbc:tc:postgresql:16:///workshop` é interpretado pelo Testcontainers — ele sobe automaticamente um container PostgreSQL 16 e destrói ao terminar os testes.

---

## Script de Validação End-to-End

```bash
chmod +x validation.sh
./validation.sh
```

Simula o fluxo completo de uma OS usando `curl`:
1. Login → obtém token
2. Cria cliente e veículo
3. Cria OS
4. Diagnóstico → reserva estoque
5. Aguarda aprovação → cliente aprova
6. Técnico executa serviços (TO_DO → DOING → DONE)
7. Finaliza OS → confirma reservas
8. Entrega veículo

---

## Cobertura Mínima Recomendada

| Nível | Meta |
|---|---|
| Geral | ≥ 70% |
| Domínio (business rules) | ≥ 85% |
| Controllers | ≥ 60% |

---

## Links Relacionados
- [[SonarQube]]
- [[Docker Compose]]
- [[Quickstart]]
