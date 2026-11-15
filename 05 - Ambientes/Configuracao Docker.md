---
title: Configuração Docker
tags:
  - ambientes
  - docker
aliases:
  - Dockerfile
  - Imagens
---

# Configuração Docker

## Dockerfile (igual nos 4 serviços)

```dockerfile
FROM maven:3.9.9-eclipse-temurin-21-alpine AS build
WORKDIR /app
COPY . .
RUN mvn clean package -DskipTests

FROM amazoncorretto:21-alpine
WORKDIR /app
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
COPY --from=build /app/target/*.jar app.jar
RUN chown -R appuser:appgroup /app
USER appuser
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
```

- **Multi-stage:** o JDK e o Maven ficam só no estágio de build; a imagem final tem só o JRE.
- **Usuário sem privilégio** (`appuser`).
- `.dockerignore` tira `target/`, `.git/` e arquivos de IDE do contexto.
- Imagem base escaneada com Trivy, sem vulnerabilidades HIGH/CRITICAL de SO —
  [[Relatorio de Vulnerabilidades - Fase 4]].

## Onde as imagens são usadas

| Ambiente | Build | Execução |
|---|---|---|
| Local | `docker compose … --profile app up --build` | [[Docker Compose]] |
| AWS | job `docker-build-push` do pipeline → **ECR** | EKS (`k8s/app.yaml` de cada serviço, com HPA e probes) |

## Configuração no container

Tudo por variável de ambiente ([[Variaveis de Ambiente]]): no compose ficam no próprio
`docker-compose.dev.yml` (com âncoras YAML para JWT e mensageria); no EKS, no
`k8s/configmap.yaml` + Secret de cada serviço.

Healthcheck: `GET /actuator/health` (compose) e `/actuator/health/readiness|liveness`
(Kubernetes).

## Links Relacionados
- [[Docker Compose]]
- [[Variaveis de Ambiente]]
