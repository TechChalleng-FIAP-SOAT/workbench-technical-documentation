---
title: SonarQube — Análise de Qualidade
tags:
  - qualidade
  - sonarqube
  - cobertura
  - jacoco
aliases:
  - Sonar
  - Code Quality
  - Análise Estática
---

# SonarQube — Análise de Qualidade

## O que é o SonarQube?

**SonarQube** é uma plataforma de **SAST** (Static Application Security Testing) e análise de qualidade de código. Analisa o código-fonte em busca de:

- **Bugs** — erros que podem causar comportamento incorreto
- **Vulnerabilidades** — falhas de segurança no código
- **Code Smells** — problemas de manutenibilidade
- **Cobertura de Testes** — % de código coberto por testes
- **Duplicações** — código repetido

---

## Configuração no Projeto

### `pom.xml`

```xml
<properties>
    <sonar.projectKey>workbench-monolith</sonar.projectKey>
    <sonar.projectName>workbench-monolith</sonar.projectName>
    <sonar.host.url>http://localhost:9000</sonar.host.url>
    <sonar.coverage.jacoco.xmlReportPaths>
        target/site/jacoco/jacoco.xml
    </sonar.coverage.jacoco.xmlReportPaths>
</properties>

<plugin>
    <groupId>org.sonarsource.scanner.maven</groupId>
    <artifactId>sonar-maven-plugin</artifactId>
    <version>5.5.0.6356</version>
</plugin>
```

### JaCoCo (Gerador de Relatório de Cobertura)

```xml
<plugin>
    <groupId>org.jacoco</groupId>
    <artifactId>jacoco-maven-plugin</artifactId>
    <version>0.8.14</version>
    <executions>
        <execution>
            <goals><goal>prepare-agent</goal></goals>
        </execution>
        <execution>
            <id>report</id>
            <phase>test</phase>
            <goals><goal>report</goal></goals>
        </execution>
    </executions>
</plugin>
```

---

## Como Rodar a Análise

### Passo 1: Garantir que o SonarQube está rodando
```bash
docker compose up -d sonarqube
# Aguardar ~2 minutos para inicializar
# Acesse: http://localhost:9000
```

### Passo 2: Rodar testes + análise
```bash
# Gera cobertura (JaCoCo) + envia para SonarQube
./mvnw clean verify sonar:sonar
```

### Passo 3: Ver resultados
Acesse `http://localhost:9000` → projeto `workbench-monolith`

---

## Credenciais Padrão do SonarQube

| Campo | Valor |
|---|---|
| URL | `http://localhost:9000` |
| Usuário | `admin` |
| Senha inicial | `admin` |

> [!warning] Altere a senha no primeiro acesso
> O SonarQube solicita troca de senha no login inicial.

---

## Autenticação com Token (Opcional)

Para ambientes CI/CD, crie um token de autenticação:

1. `http://localhost:9000` → My Account → Security → Generate Token
2. Use o token:
```bash
./mvnw sonar:sonar -Dsonar.token=squ_xxxxxxxxxxxx
```

---

## Métricas Monitoradas

| Métrica | Descrição | Meta Sugerida |
|---|---|---|
| **Coverage** | % de linhas cobertas por testes | ≥ 70% |
| **Duplications** | % de código duplicado | ≤ 3% |
| **Reliability Rating** | Severidade dos bugs (A-E) | A |
| **Security Rating** | Severidade das vulnerabilidades (A-E) | A |
| **Maintainability Rating** | Technical debt ratio (A-E) | A |
| **Lines of Code** | Total de linhas | — |

---

## Quality Gate

O Quality Gate define se o projeto passa ou falha na análise:

**Condições padrão do Quality Gate "Sonar Way":**
- Coverage em código novo ≥ 80%
- Duplicação em código novo ≤ 3%
- Reliability Rating = A
- Security Rating = A
- Maintainability Rating = A

> [!info] Branches no SonarQube
> O projeto tem branches `feature/sonarqube` e `feature-sonar-docker` no git, indicando que a integração com SonarQube foi desenvolvida incrementalmente.

---

## Integração no Docker Compose

```yaml
sonarqube:
  image: sonarqube:community
  ports:
    - "9000:9000"
  environment:
    SONAR_JDBC_URL: jdbc:postgresql://sonarqube_db:5432/sonar
    SONAR_JDBC_USERNAME: sonar
    SONAR_JDBC_PASSWORD: sonar
  depends_on:
    sonarqube_db:
      condition: service_healthy
```

> [!warning] SonarQube e Memória
> O SonarQube Community requer ~2GB de RAM. Em máquinas com menos de 8GB, considere subir apenas quando for analisar.

---

## Relatório Local JaCoCo (Sem SonarQube)

Para ver a cobertura sem o SonarQube:

```bash
./mvnw test jacoco:report
# Abra no browser:
open target/site/jacoco/index.html
```

---

## Links Relacionados
- [[Rodando Testes]]
- [[Docker Compose]]
- [[OWASP ZAP]]
- [[Tecnologias]]
