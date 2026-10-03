# Known Limitations

**If a capability is not listed as implemented here, assume it is not.**

This page exists so that nobody has to guess, and so that no feature is described
as finished when it is only partial. Each entry says what is missing and what the
current behaviour actually is.

Last reviewed: Phase 7 (Company Environment Finalization).

---

## Security

| # | Limitation | Impact | Workaround | Tracked |
| - | ---------- | ------ | ---------- | ------- |
| S1 | **DNS rebinding window** between host validation and connection | A hostile DNS server could redirect a validated host to an internal address | Keep `DATASOURCE_ALLOW_PRIVATE_NETWORKS=false`; restrict egress at the network layer | VM-1 |
| S2 | **No antivirus / content disarm** on uploads | A malicious document may reach pypdf/python-docx | Containers run non-root with no privileged mounts; scan at the edge | VM-2 |
| S3 | **No Content-Security-Policy** header | Reduced defence in depth against XSS | Tokens are httpOnly, so XSS cannot steal a session | VM-3 |
| S4 | **Redis has no authentication** in the local stack | Anyone with network access to Redis can read the broker | Local-only; set `requirepass` and isolate the network in production | VM-4 |
| S5 | **No managed secrets vault** or rotation automation | Secrets are environment variables; rotation is manual | Rotate via `.env` + restart | VM-5 |
| S6 | **No Fernet re-encryption command** | `DATAFORGE_FERNET_KEY` cannot be cleanly rotated | Keep the key safe; back it up | VM-6 |
| S7 | **Rate limits are per process** | Effective limit multiplies with worker count | Enforce at the edge | VM-7 |
| S8 | **Tenant scoping is guarded, not compiler-enforced** | A future selector could still forget the organization filter; the boundary check catches client-controlled scope and header fallbacks, but cannot prove every query is scoped | Centralized `require_organization()` + `scripts/dev/check_boundaries.py` + tenant-isolation tests | VM-8 |
| S10 | **No alerting on security events** | Detection depends on someone reading audit logs | Review audit logs manually | VM-10 |
| S11 | **No dependency-update automation** | Vulnerable dependencies surface only via the weekly `pip-audit` | Watch the weekly security workflow | VM-11 |

## Authentication

| # | Limitation | Current behaviour |
| - | ---------- | ----------------- |
| A1 | **No multi-factor authentication** | Password only |
| A2 | **No password reset by email** | No mail provider is wired up; an admin must change the password in the Django admin |
| A3 | **No SSO / OIDC / SAML** | Local accounts only |
| A4 | **No email verification** | Accounts are created administratively or by seed |
| A5 | **No per-session revocation UI** | Changing your password signs out all sessions |
| A6 | **No user self-registration** | Accounts are provisioned by an owner/admin (and `seed_development`) |

## Authorization

| # | Limitation | Current behaviour |
| - | ---------- | ----------------- |
| Z1 | **No per-resource ACL** | Organization + role only; every member sees every resource in the organization |
| Z2 | **Owner and admin have the same permission set** | Ownership is additionally protected by the last-owner invariant |
| Z3 | **No time-bounded or delegable roles** | Roles are permanent until changed |
| Z4 | **No audit of permission *reads*** | Only state changes are audited |

## AI service

| # | Limitation | Current behaviour |
| - | ---------- | ----------------- |
| I1 | **No streaming tokens to the client** | The analyst returns the finished answer; partial output is not streamed |
| I2 | **Single-model prompt strategy** | No routing between models by task or cost |
| I3 | **No conversation memory across runs** | Each run is independent; there is no multi-turn thread object |
| I4 | **No query-result caching** | Every analyst run re-executes its SQL |
| I5 | **Embedding dimension is fixed by migration** | Changing `EMBEDDING_DIM` requires a new migration and re-embedding |
| I6 | **Chunking is character-based, not token-based** | Approximate; adequate but not optimal for token budgeting |
| I7 | **No re-ranking of retrieved passages** | Cosine similarity only |
| I8 | **Base64 document payload to the AI service** | A ~25 MB file becomes a ~33 MB request; bounded by `_MAX_INLINE_BYTES` |
| I9 | **Prompt-injection detection is heuristic** | It flags patterns; it does not understand intent. Safety comes from structural controls, not detection |
| I10 | **No cost tracking or budget limits** | Token usage is recorded, but no spend cap is enforced |

## Product / UI

| # | Limitation | Current behaviour |
| - | ---------- | ----------------- |
| U1 | **Browser-side WebSocket client is not wired up** | The server-side consumer, JWT middleware, broadcast and group scoping are implemented and the API broadcasts events. The UI refreshes by navigation rather than subscribing live |
| U2 | **"Conversations" and "Reports/Insights" are not separate pages** | Analyst runs are visible in Execution History and the dashboard shows aggregate insights. This is deliberate: no separate feature was invented to fill the menu |
| U3 | **No organization creation UI for brand-new users** | An owner creates an organization via the API (`POST /api/v1/orgs/`); a UI for it is not built. A user with no membership sees `/no-organization` |
| U4 | **No document preview** | Only metadata and status are shown |
| U5 | **No bulk actions** | Actions are per row |
| U6 | **No dark theme** | Light only |
| U7 | **No internationalisation** | English only |
| U8 | **No data export** | Audit logs and executions cannot be exported to CSV/JSON yet |

## Database and operations

| # | Limitation | Current behaviour |
| - | ---------- | ----------------- |
| D1 | **No automated backups** | A deployment responsibility; not configured here |
| D2 | **No data retention policy** | Executions and audit logs are kept indefinitely |
| D3 | **Software is not partitioned by age** | Single-table `audit_logs`; will need partitioning at volume |
| D4 | **No read replica or connection pooling** | Direct connections with `CONN_MAX_AGE=60` |
| D5 | **Tests require PostgreSQL** | SQLite is not supported because the schema uses pgvector; see `config/settings/test.py` |
| D6 | **`pgvector` HNSW index is created at migration time** | Index build parameters are not tuned for large corpora |

## Deployment

| # | Limitation | Current behaviour |
| - | ---------- | ----------------- |
| P1 | **The deploy workflow does not deploy anywhere** | It builds and publishes images and is gated behind `DEPLOY_ENABLED`; no target environment is configured |
| P2 | **No TLS/nginx configuration in the repo** | `infrastructure/nginx/` documents the expected reverse-proxy behaviour; no certificates |
| P3 | **No Kubernetes manifests** | Docker Compose only |
| P4 | **No observability stack** | Structured logs and per-service health endpoints only; no metrics, traces or dashboards |
| P5 | **No load or performance testing** | `tests/performance/` describes what should be measured; no benchmark suite is implemented, and **no performance claims are made** anywhere in this repository |
| P6 | **No E2E test executed in CI** | `tests/e2e/` contains a script that requires a running stack; CI does not start one |

## Explicitly out of scope for this release

These are not gaps — they are deliberate product boundaries:

- Connectors other than PostgreSQL and MySQL.
- Write-back to customer databases (the platform is read-only by design).
- Multi-region or high-availability deployment.
- A general-purpose BI/reporting builder.
- Non-English content processing.

---

## How to add an entry

When you ship something partial, add a row here **in the same pull request**. Be
specific about current behaviour — "not implemented" is fine, "coming soon" is not.
