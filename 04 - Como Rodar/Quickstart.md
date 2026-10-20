---
title: Quickstart — Subir o Projeto
tags:
  - como-rodar
  - quickstart
  - setup
aliases:
  - Como Rodar
  - Setup
---

# Quickstart — Subir o Projeto

> [!tip] Em 5 minutos
> Siga os passos abaixo para ter o projeto rodando localmente com banco de dados e dados de teste pré-carregados.

## Pré-requisitos

- [ ] Java 21 JDK instalado (`java -version`)
- [ ] Docker e Docker Compose instalados (`docker --version`)
- [ ] Portas livres: **5432** (PostgreSQL), **8080** (App), **9000** (SonarQube)

---

## Passo 1 — Clonar o Repositório

```bash
git clone <url-do-repositorio>
cd workbench-monolith
```

---

## Passo 2 — Subir a Infraestrutura (Banco de Dados)

```bash
docker compose up -d
```

Isso sobe:
- **PostgreSQL 16** em `localhost:5432`
- Executa `init.sh` automaticamente — cria tabelas + semeia dados de teste

> [!info] Aguardar Inicialização
> Na primeira execução, o PostgreSQL leva ~30 segundos para estar pronto. Verifique com:
> ```bash
> docker compose logs postgres
> ```

---

## Passo 3 — Rodar a Aplicação

```bash
./mvnw spring-boot:run
```

A aplicação inicia em `http://localhost:8080`.

---

## Passo 4 — Verificar que Está Rodando

```bash
# Deve retornar 200 (redireciona para Swagger UI)
curl -I http://localhost:8080/swagger-ui/index.html
```

Acesse: **http://localhost:8080/swagger-ui/index.html**

---

## Passo 5 — Fazer Login e Testar

```bash
# Obter token JWT
TOKEN=$(curl -s -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"superadmin@system.com","password":"coxinha123"}' \
  | jq -r '.token')

# Usar o token
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8080/api/clients
```

**Credenciais padrão:**
- Email: `superadmin@system.com`
- Senha: `coxinha123`

---

## Executar Fluxo Completo de Validação

```bash
chmod +x validation.sh
./validation.sh
```

Este script simula um ciclo completo: criação de OS → diagnóstico → reserva de estoque → orçamento → aprovação → execução → finalização → entrega.

---

## Atalhos Úteis

| O que fazer | Comando |
|---|---|
| Ver logs da aplicação | `docker compose logs app -f` |
| Ver logs do banco | `docker compose logs postgres -f` |
| Parar tudo | `docker compose down` |
| Parar e apagar volumes | `docker compose down -v` |
| Recompilar e rodar | `./mvnw clean spring-boot:run` |

---

## Próximos Passos

- Ver todos os endpoints: [[00 - Home#Rotas da API]]
- Entender o fluxo de negócio: [[Ciclo de Vida da OS]]
- Rodar testes: [[Rodando Testes]]
- Configurar variáveis: [[Variaveis de Ambiente]]

## Links Relacionados
- [[Requisitos]]
- [[Docker Compose]]
- [[Credenciais e Seeds]]
