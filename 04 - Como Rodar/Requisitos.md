---
title: Requisitos e Pré-requisitos
tags:
  - como-rodar
  - requisitos
  - instalacao
---

# Requisitos e Pré-requisitos

## Requisitos de Sistema

| Componente | Versão Mínima | Como Verificar |
|---|---|---|
| Java JDK | 21 LTS | `java -version` |
| Maven | 3.9+ (ou usar `./mvnw`) | `./mvnw -version` |
| Docker | 24+ | `docker --version` |
| Docker Compose | 2.x | `docker compose version` |

> [!tip] Maven Wrapper
> O projeto inclui `mvnw` (Maven Wrapper). Você **não precisa** instalar Maven globalmente — use sempre `./mvnw` em vez de `mvn`.

---

## Portas Necessárias

| Porta | Serviço | Conflito Comum |
|---|---|---|
| **5432** | PostgreSQL | Postgres local já rodando |
| **8080** | Spring Boot App | Outro servidor na porta |
| **9000** | SonarQube | Outro serviço |

Verificar portas em uso no Linux/Mac:
```bash
lsof -i :5432 && lsof -i :8080 && lsof -i :9000
```

Verificar portas em uso no Windows:
```powershell
netstat -ano | findstr "5432 8080 9000"
```

---

## Configurações de Hardware Recomendadas

| Recurso | Mínimo | Recomendado |
|---|---|---|
| RAM | 4 GB | 8 GB (SonarQube consome ~1.5GB) |
| CPU | 2 cores | 4 cores |
| Disco | 5 GB livre | 10 GB livre |

> [!warning] SonarQube é Pesado
> O SonarQube requer pelo menos 2 GB de RAM dedicados. Se sua máquina for limitada, rode apenas o banco e a aplicação:
> ```bash
> docker compose up -d postgres
> ./mvnw spring-boot:run
> ```

---

## Instalação do Java 21

### Windows (via Winget)
```powershell
winget install Microsoft.OpenJDK.21
```

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install openjdk-21-jdk
```

### Mac (via Homebrew)
```bash
brew install openjdk@21
```

---

## Variáveis de Ambiente de Sistema

O Maven Wrapper detecta `JAVA_HOME` automaticamente. Se houver problemas:

```bash
# Linux/Mac
export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64

# Windows PowerShell
$env:JAVA_HOME = "C:\Program Files\Java\jdk-21"
```

---

## Links Relacionados
- [[Quickstart]]
- [[Docker Compose]]
- [[Variaveis de Ambiente]]
