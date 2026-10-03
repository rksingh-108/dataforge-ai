# Security Architecture

## Trust boundaries

```
        untrusted                     semi-trusted                    trusted
 ┌──────────────────┐         ┌──────────────────────┐        ┌──────────────────┐
 │  Browser         │  HTTPS  │  Next.js BFF         │  HTTP  │  Django API      │
 │  (hostile input) │ ──────▶ │  httpOnly cookies    │ ─────▶ │  authz authority │
 └──────────────────┘         └──────────────────────┘        └────────┬─────────┘
                                                                       │ service token
                                                                       ▼
                                                     ┌──────────────────────────────┐
                                                     │  AI service                  │
                                                     │  egress broker, no platform  │
                                                     │  DB access                   │
                                                     └──────┬────────────────┬──────┘
                                                            │                │
                                                    LLM/embedding     customer DBs
                                                      vendors         (read-only)
```

Three boundaries matter:

1. **Browser → BFF.** Everything from the browser is untrusted. The BFF holds the
   only copy of the session tokens.
2. **BFF/API → AI service.** Authenticated with a shared service token and an
   explicit organization scope. The AI service never writes platform data.
3. **AI service → customer database / LLM vendor.** The only place data leaves the
   platform. Subject to SQL validation, read-only sessions and the host guard.

## Data classification

| Class | Examples | Handling |
| ----- | -------- | -------- |
| Secret | `DJANGO_SECRET_KEY`, Fernet key, service token, provider keys | Environment only; never logged; never serialized |
| Restricted | Data-source passwords | Fernet-encrypted at rest; decrypted only in-process; access audited |
| Confidential | Tenant documents, query results, answers | Tenant-scoped; TLS in transit; never sent to a vendor except as prompt context |
| Internal | Executions, audit logs, schema metadata | Tenant-scoped; retained for audit |
| Public | Marketing copy, docs | None |

## Cryptography

| Purpose | Algorithm | Notes |
| ------- | --------- | ----- |
| Password hashing | Django default (PBKDF2-SHA256, upgradeable) | Never reversible |
| Credential encryption at rest | Fernet (AES-128-CBC + HMAC-SHA256) | Authenticated; fails closed |
| Session tokens | JWT HS256, signed with `DJANGO_SECRET_KEY` | Short-lived access, rotating refresh |
| Transport | TLS terminated at the edge | HSTS in production settings |

We use vetted libraries (`cryptography`, `djangorestframework-simplejwt`). No
custom cryptography anywhere in this repository, by policy.

## Authentication flows

| Actor | Mechanism |
| ----- | --------- |
| User | Email + password → JWT access (15 min) + refresh (7 days); tokens in httpOnly cookies behind the BFF |
| AI service | `Authorization: Bearer <INTERNAL_SERVICE_TOKEN>` + `X-DataForge-Org` |
| WebSocket | JWT access token in the connect query string; membership re-checked at connect |

## Logging

- Structured, with a per-request correlation id propagated from web → api → ai
  (`X-Request-Id`).
- Secrets are scrubbed by `RedactingFormatter` before a record is emitted.
- Security-relevant events are written to the append-only `AuditLog`, not just to
  logs.

## Network posture (production, recommended)

| Service | Exposure |
| ------- | -------- |
| web | Public (TLS) |
| api | Reachable only from web and the AI service; not public |
| ai-service | Reachable only from api; **never public** — it is an egress broker |
| postgres, redis | Private network only |

The local Compose file publishes all ports for developer convenience. That is a
development topology, not a deployment recommendation.
