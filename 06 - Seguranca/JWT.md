---
title: JWT — Autenticação por Token
tags:
  - seguranca
  - jwt
  - autenticacao
aliases:
  - JSON Web Token
  - Token JWT
---

# JWT — Autenticação por Token

## Visão Geral

O sistema usa **JWT (JSON Web Token)** com algoritmo **HS256** para autenticação stateless. Não há sessão no servidor — cada requisição carrega o token com todas as informações necessárias.

---

## Geração do Token (`JwtService.java`)

```java
public String generateToken(User user) {
    long now = System.currentTimeMillis();
    return Jwts.builder()
        .subject(user.getEmail())                           // sub: email do usuário
        .claim("userId", user.getId().toString())           // claim customizado
        .claim("roles", user.getRoles().stream()
            .map(Role::getName).toList())                   // claim de roles
        .issuedAt(new Date(now))                            // iat: emissão
        .expiration(new Date(now + props.getExpiration()))  // exp: expiração
        .signWith(key)                                      // assina com HS256
        .compact();
}
```

### Chave de Assinatura

```java
// Derivada do secret via HMAC-SHA256
SecretKey key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
```

---

## Claims do Token

| Claim | Tipo | Descrição |
|---|---|---|
| `sub` | String | Email do usuário autenticado |
| `userId` | String (UUID) | ID único do usuário |
| `roles` | Array | Lista de roles (`["ROLE_ADMIN", "ROLE_USER"]`) |
| `iat` | Long | Timestamp de emissão (Unix) |
| `exp` | Long | Timestamp de expiração (Unix) |

**Exemplo de payload decodificado:**
```json
{
  "sub": "superadmin@system.com",
  "userId": "550e8400-e29b-41d4-a716-446655440000",
  "roles": ["ROLE_ADMIN", "ROLE_USER", "ROLE_TECHNICIAN"],
  "iat": 1705312800,
  "exp": 1705399200
}
```

---

## Validação do Token (`JwtFilter.java`)

O `JwtFilter` intercepta **todas** as requisições (exceto endpoints públicos):

```java
@Component
public class JwtFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request, ...) {
        // 1. Extrai o header Authorization
        String header = request.getHeader("Authorization");
        if (header == null || !header.startsWith("Bearer ")) {
            filterChain.doFilter(request, response);
            return;
        }

        // 2. Extrai o token
        String token = header.substring(7);

        // 3. Valida assinatura e expiração
        Claims claims = jwtService.extractClaims(token);

        // 4. Define o contexto de segurança
        UsernamePasswordAuthenticationToken auth = new UsernamePasswordAuthenticationToken(
            claims.getSubject(), null, authorities
        );
        SecurityContextHolder.getContext().setAuthentication(auth);

        filterChain.doFilter(request, response);
    }
}
```

---

## Configuração (`JwtProperties.java`)

```java
@ConfigurationProperties(prefix = "jwt")
public record JwtProperties(
    String secret,       // JWT_SECRET env var
    long expiration      // JWT_EXPIRATION env var (padrão: 86400000ms = 24h)
) {}
```

**Valores configurados via variáveis de ambiente:**
```yaml
jwt:
  secret: ${JWT_SECRET:akmsdkmasfnjsgknakmsdkmasdkmsadfkmdsakmdkmsadsa}
  expiration: ${JWT_EXPIRATION:86400000}
```

---

## Gerenciamento de Sessão

```java
// SecurityConfig.java
.sessionManagement(session ->
    session.sessionCreationPolicy(SessionCreationPolicy.STATELESS)
)
```

> [!info] Stateless
> Nenhuma sessão é criada no servidor. Cada requisição é autenticada independentemente pelo token JWT. Isso permite escalabilidade horizontal sem necessidade de session store compartilhado.

---

## Como Usar o Token

### Via curl
```bash
# 1. Login
TOKEN=$(curl -s -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"superadmin@system.com","password":"coxinha123"}' \
  | jq -r '.token')

# 2. Usar nas requisições
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8080/api/clients
```

### Via Swagger UI
1. Acesse `http://localhost:8080/swagger-ui/index.html`
2. Clique em **Authorize** (cadeado)
3. Cole o token no campo `Bearer Token`
4. Todas as requisições do Swagger incluirão o token automaticamente

---

## Segurança do JWT_SECRET

> [!danger] Segredo Padrão é Público
> O segredo padrão no código-fonte é conhecido publicamente. **Sempre** substitua via variável de ambiente em qualquer ambiente além do desenvolvimento local.

**Requisito mínimo:** 256 bits (32 bytes) para algoritmo HS256.

```bash
# Gerar segredo seguro
openssl rand -base64 64
```

---

## Erros Comuns

| Código | Motivo |
|---|---|
| 401 | Token ausente, inválido ou expirado |
| 403 | Token válido mas role insuficiente |

---

## Links Relacionados
- [[Autorizacao e Roles]]
- [[Spring Security Config]]
- [[API - Autenticacao]]
- [[Variaveis de Ambiente]]
