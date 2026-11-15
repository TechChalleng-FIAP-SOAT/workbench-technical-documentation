---
title: Relatório de Vulnerabilidades — Fase 4
tags:
  - seguranca
  - owasp
  - zap
  - trivy
  - relatorio
aliases:
  - Relatório de Vulnerabilidades
  - Scan de Segurança Fase 4
---

# Relatório de Vulnerabilidades — Fase 4 (microsserviços)

**Data:** 11/11/2026 · **Escopo:** os-service, customer-service, billing-service,
execution-service (código das branches de trabalho) e workbench-lambda.

| Camada | Ferramenta | Onde roda |
|---|---|---|
| **DAST** (aplicação em execução) | OWASP ZAP 2.16.1, API scan pela spec OpenAPI | Local: plataforma inteira no compose, ataques **pelo gateway** ([[OWASP ZAP]]) |
| **SCA** (dependências e imagem) | Trivy 0.57.1, severidade HIGH/CRITICAL | Imagens Docker dos 4 serviços + `pom.xml` da Lambda |
| **SAST** (código) | SonarCloud | Job `code-analysis` de cada pipeline (Quality Gate) |

## Resumo

| | Antes | Depois |
|---|---|---|
| Trivy — CRITICAL (por serviço) | 11–12 | **0** |
| Trivy — HIGH (por serviço) | 35–48 | **0** |
| Trivy — Lambda (HIGH) | 8 | **0** |
| ZAP — High / Medium | 0 | **0** |
| ZAP — FAIL do `rules.conf` (injeção, XSS, XXE, Spring4Shell…) | 0 | **0** |
| ZAP — WARN por serviço | 3 (Spectre, Content-Type, versão do ZAP) | **0** |

Nenhuma vulnerabilidade de risco alto ou médio ficou aberta.

## 1. SCA — dependências (Trivy)

### Achados

Os 4 serviços tinham as mesmas bibliotecas vulneráveis, todas trazidas pelo **Spring Boot
4.0.5** (versões gerenciadas pelo BOM):

| Biblioteca | Versão | CVEs (exemplos) | Severidade máx. | Corrigida em |
|---|---|---|---|---|
| `tomcat-embed-core` | 11.0.20 | CVE-2026-41293, CVE-2026-65182, CVE-2026-68525 | CRITICAL | 11.0.25+ |
| `spring-webmvc` | 7.0.6 | CVE-2026-47884, CVE-2026-47890 | CRITICAL | 7.0.9+ |
| `spring-boot` | 4.0.5 | CVE-2026-40976 | CRITICAL | 4.0.6+ |
| `netty-handler` (via AWS SDK) | 4.2.12 | CVE-2026-75595 | CRITICAL | 4.2.17+ |
| `jackson-core/databind` (2.x e 3.x) | 2.21.2 / 3.1.0 | CVE-2026-54512, CVE-2026-91776 | HIGH | 2.21.7 / 3.1.7 |
| `spring-security-config` | 7.0.4 | CVE-2026-22753, CVE-2026-22754 | HIGH | 7.0.5+ |
| `postgresql` | 42.7.10 | CVE-2026-42198, CVE-2026-54291 | HIGH | 42.7.12+ |
| `spring-data-commons` / `-mongodb` | 4.0.4 / 5.0.4 | CVE-2026-41695, CVE-2026-41717 | HIGH | 4.0.6 / 5.0.6 |
| `micrometer-core` | 1.16.4 | CVE-2026-40983 | HIGH | 1.16.6 |

Na Lambda: `jackson-core/databind` 2.18.2 (8 HIGH).

### Correção

- **Spring Boot 4.0.5 → 4.0.9** nos 4 serviços (mesma linha 4.0, só patch). O BOM novo traz
  Tomcat 11.0.27, Spring 7.0.10, Spring Security 7.0.8, Jackson 3.1.7/2.21.7, Netty 4.2.19,
  driver Postgres 42.7.14 e Micrometer 1.16.8.
- **Lambda:** `jackson.version` 2.18.2 → 2.18.11.
- Os 4 serviços e a Lambda passaram no `mvn verify` depois da troca (431 testes nos serviços).
- **Reteste:** Trivy nas imagens reconstruídas e no `pom.xml` da Lambda → 0 HIGH/CRITICAL.
  A imagem base (`amazoncorretto:21-alpine`) não teve achados de SO.

## 2. DAST — aplicação em execução (OWASP ZAP)

Cada serviço foi escaneado pela sua spec OpenAPI, com token de ADMIN, atacando através do
gateway local (mesmo roteamento do API Gateway da AWS). Cerca de 115 regras por serviço
(ativas e passivas).

### Primeira rodada

| ID | Alerta | Risco | Análise | Ação |
|---|---|---|---|---|
| 90004 | Insufficient Site Isolation Against Spectre | Low | Faltavam `Cross-Origin-Resource-Policy`, `-Opener-Policy` e `-Embedder-Policy` | **Corrigido**: os 3 cabeçalhos no Spring Security dos 4 serviços, com teste de integração |
| 100001 | Unexpected Content-Type | Low | O 401 saía sem corpo e sem `Content-Type`; o nginx local respondia HTML a requisição malformada | **Corrigido**: 401/403 em JSON (`JsonSecurityErrorHandler`, no formato dos demais erros e em português) e páginas de erro do gateway local em JSON |
| 10116 | ZAP is Out of Date | Low | Aviso da própria ferramenta (imagem fixada) | `IGNORE` no `rules.conf`, com justificativa |
| 10096 | Timestamp Disclosure (execution) | Low | Datas `createdAt`/`updatedAt` legítimas na resposta | Já era `IGNORE` |
| 100000 / 10104 / 10049 | Erro 4xx, User Agent Fuzzer, conteúdo não armazenável | Info | Respostas 400/404 esperadas a parâmetros inválidos; `no-store` é o desejado para API | Nenhuma |

### Rodada final (depois das correções)

| Serviço | FAIL | WARN | PASS | Alertas restantes |
|---|---|---|---|---|
| os-service | 0 | 0 | 114 | só informativos (4xx esperados, fuzzer de User-Agent, `no-store`) |
| customer-service | 0 | 0 | 114 | idem + 10111 "Authentication Request Identified" (rota de login interna, esperado) |
| billing-service | 0 | 0 | 114 | idem |
| execution-service | 0 | 0 | 113 | idem + 10096 timestamp (ignorado, ver acima) |

O alerta 100001 também vinha de uma página HTML do **nginx local** (linha de requisição sem
barra, `GET ?aaa=bbb`); o gateway local passou a responder esses erros em JSON. Na AWS esse
papel é do API Gateway.

### Achados do próprio teste ponta a ponta (fora do ZAP)

Ao rodar o fluxo completo pelo gateway, encontramos e corrigimos dois pontos de **OWASP A05
(Security Misconfiguration / vazamento de informação)**:

- UUID ou JSON inválido devolvia 422/500 com a **mensagem técnica do Jackson/SQL** →
  agora é 400 com mensagem em português; erro inesperado vira 500 genérico (o detalhe vai só
  para o log); 405/415 mantêm o status certo.
- SKU duplicado devolvia 500 → 409.

## 3. SAST — SonarCloud

Roda no job `code-analysis` de cada serviço, a cada PR para `main`/`develop`, com o Quality
Gate e o gate de cobertura (80%) do JaCoCo. Prints do painel entram no PDF de entrega.

## 4. Controles já existentes (revisados)

- JWT HS256 validado em todos os serviços; authorizer Lambda no API Gateway.
- Autorização por perfil + **dono do recurso** (cliente só acessa a própria OS, orçamento,
  pagamento, cadastro e veículos).
- Login de staff com bloqueio após 5 erros seguidos (15 min).
- `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Cache-Control: no-store`.
- Sessão stateless; CSRF desligado de propósito (API com Bearer, sem cookie).
- Webhook de pagamento simulado só existe com `PAYMENT_PROVIDER=fake` (local). Em produção a
  confirmação vem do job que consulta o Mercado Pago.
- Segredos fora do código (GitHub Secrets → Kubernetes Secrets / Secrets Manager).

## 5. Como repetir

```bash
cd workbench-messaging
docker compose -f docker-compose.dev.yml --profile app up -d --build
zap/scan-platform.sh                                      # DAST, relatórios em zap-reports/
for s in os customer billing execution; do                # SCA
  docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:0.57.1 \
    image --scanners vuln --severity HIGH,CRITICAL workbench-messaging-$s-service:latest
done
```

## Links Relacionados
- [[OWASP ZAP]]
- [[Spring Security Config]]
- [[JWT]]
- [[SonarQube]]
