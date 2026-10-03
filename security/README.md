# Security Engineering

This directory is owned by the **Cybersecurity** team (see
[`.github/CODEOWNERS`](../.github/CODEOWNERS)). It contains the security
artefacts for DataForge AI: threat models, the security architecture, policies,
vulnerability management, incident response and the security test strategy.

Security is not an afterthought in this repository. It is a review gate: changes
that touch authentication, authorization, tenancy, credentials, outbound network
calls or AI tool execution require a security owner's approval.

## Honesty rule

> **Nothing in this directory may claim a control is in place unless it is
> actually implemented and tested.**

Every control below states where it lives in the code and how it is verified. If
a control is partial, it says so. Gaps live in
[`vulnerability-management/README.md`](vulnerability-management/README.md) and
[`../docs/development/known-limitations.md`](../docs/development/known-limitations.md).

## What we protect

| Asset                        | Why it matters                                             |
| ---------------------------- | ---------------------------------------------------------- |
| Tenant business data         | The product's whole value; cross-tenant leakage is fatal   |
| Data-source credentials      | Grant read access to customer databases                    |
| Uploaded documents           | Internal, often confidential                               |
| AI executions and audit logs | Evidence of what the AI did and who asked                  |
| Session tokens               | Account takeover if leaked                                 |
| LLM provider keys            | Cost and data exposure if leaked                           |

## Control map

| Threat                      | Control                                                                                  | Where it lives                                                            | Verified by |
| --------------------------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- | ----------- |
| Cross-tenant data access    | Org scope derives only from the URL `org_id` → verified membership (`require_organization`); the client-controlled `X-Organization-Id` header is ignored; object routes return 404, not 403 | `apps/api/apps/common/permissions.py`, `*/selectors.py` | `apps/api/tests/security/test_tenant_isolation.py`, `test_tenant_scope_resolution.py`, `scripts/dev/check_boundaries.py` |
| Privilege escalation        | Server-side RBAC matrix; UI hiding is never a control                                    | `apps/api/apps/common/rbac.py`                                             | `apps/api/tests/security/test_authorization_matrix.py` |
| Password / token weakness   | Django password validators, short-lived access token, rotating + blacklisted refresh     | `config/settings/base.py` (`SIMPLE_JWT`), `apps/accounts/views.py`         | `apps/api/apps/accounts/tests/test_auth.py` |
| Token theft via XSS         | Tokens are httpOnly cookies behind the web BFF; no token reaches JavaScript              | `apps/web/lib/session.ts`, `apps/web/app/api/proxy/[...path]/route.ts`      | Code review; `apps/web/lib/*.test.ts` for gating logic |
| SQL injection / data loss   | AST-level parser validation, read-only sessions, statement timeouts, row caps            | `apps/ai-service/ai_service/sql/validator.py`, `connections/`              | `apps/ai-service/tests/test_sql_validator.py` (29 tests) |
| SSRF                        | Outbound host classification at create time *and* at connect time                        | `apps/api/apps/datasources/validators.py`, `ai_service/security/host_guard.py` | `apps/api/apps/datasources/tests/`, `apps/ai-service/tests/test_security.py` |
| Prompt injection            | Untrusted-content delimiting, heuristic detection, and structural safety (validation does not trust the model) | `ai_service/security/injection.py`, `sql/validator.py`                     | `apps/ai-service/tests/test_security.py`, `test_sql_validator.py` |
| Malicious file upload       | Extension + declared type + magic bytes + size + checksum dedupe                         | `apps/api/apps/documents/validators.py`                                    | `apps/api/apps/documents/tests/test_documents.py` |
| Credential exposure at rest | Fernet encryption; credentials never serialized; access audited                          | `apps/api/apps/common/crypto.py`, `apps/datasources/models.py`, `internal_views.py` | `apps/api/apps/datasources/tests/`, `apps/api/apps/ai_bridge/tests/test_internal_endpoints.py` |
| Internal API exposure       | Shared service token (constant-time compare) + mandatory `X-DataForge-Org` scope, validated as a UUID and applied to scoped selectors | `apps/api/apps/common/service_auth.py`, `ai_service/security/internal_auth.py` | `apps/api/apps/ai_bridge/tests/test_internal_endpoints.py`, `apps/api/tests/security/test_tenant_scope_resolution.py` |
| WebSocket authorization     | JWT from query string; membership re-checked on connect; 4401 unauthenticated / 4403 non-member; per-org channel groups | `apps/api/apps/realtime/consumers.py`, `apps/common/ws_auth.py` | `apps/api/apps/realtime/tests/test_websocket_auth.py` |
| API abuse                   | Scoped DRF throttles (`auth`, `analyst`, `default`)                                      | `config/settings/base.py` (`REST_FRAMEWORK`)                               | `apps/api/tests/security/test_rate_limiting.py` |
| Tampering with history      | Append-only audit model (updates and deletes raise)                                      | `apps/api/apps/common/models.py`, `apps/analytics/models.py`               | `apps/api/apps/analytics/tests/test_executions.py` |
| Committed secrets           | Pattern scan of tracked files; `.env` ignored                                            | `scripts/dev/scan_secrets.sh`, `.gitignore`                                | `security.yml` workflow |

## Directory guide

| Path | Contents |
| ---- | -------- |
| [`threat-model/`](threat-model/) | STRIDE-style threat models per surface, with mitigations and residual risk |
| [`security-architecture/`](security-architecture/) | Trust boundaries, data classification, crypto and secret handling |
| [`policies/`](policies/) | The rules engineers must follow (secure coding, review gates) |
| [`vulnerability-management/`](vulnerability-management/) | Severity model, SLAs, current open items, dependency process |
| [`incident-response/`](incident-response/) | Severity levels, roles, timeline, postmortem template |
| [`access-control/`](access-control/) | The RBAC matrix and tenant isolation rules in one place |
| [`secrets-management/`](secrets-management/) | How secrets are generated, stored, rotated and never committed |
| [`security-testing/`](security-testing/) | What security tests exist, what they cover, and how to add one |

## Reporting a vulnerability

See [SECURITY.md](../SECURITY.md). Private disclosure only — never a public issue.

## Known gaps (summary)

These are tracked, not hidden:

- No DNS-rebinding-resistant outbound connection (resolved-then-connect window).
- Redis has no authentication in the local stack.
- No automated dependency-update bot yet.
- No WAF or rate limiting at the edge; throttle limits are application-level only.
- Uploaded files are validated but not antivirus-scanned.

Full detail and ownership: [`vulnerability-management/README.md`](vulnerability-management/README.md).
