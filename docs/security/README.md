# Security Documentation

The security documentation lives in [`security/`](../../security/) because that
directory is owned by the cybersecurity team and is a required review path.

Start with [security/README.md](../../security/README.md) — it contains the control
map, where every control lives in the code, and the test that proves it.

## Index

| Document | Contents |
| -------- | -------- |
| [security/README.md](../../security/README.md) | Control map, assets, gaps summary |
| [threat-model/](../../security/threat-model/) | Seven STRIDE models: web/session, multi-tenancy, SQL injection, SSRF, prompt injection, file upload, secrets |
| [security-architecture/](../../security/security-architecture/) | Trust boundaries, data classification, cryptography, network posture |
| [policies/](../../security/policies/) | Twelve enforceable engineering rules |
| [access-control/](../../security/access-control/) | The RBAC matrix and tenancy rules |
| [vulnerability-management/](../../security/vulnerability-management/) | Severity model, SLAs, eleven tracked open items |
| [incident-response/](../../security/incident-response/) | Severity levels, roles, containment playbook, postmortem template |
| [secrets-management/](../../security/secrets-management/) | Generation, storage, handling, rotation |
| [security-testing/](../../security/security-testing/) | What security tests exist and how to add one |

## Quick reference: what is enforced where

| Concern | Enforced in |
| ------- | ----------- |
| Tenant isolation | `apps/api/apps/common/permissions.py`, `*/selectors.py` |
| RBAC | `apps/api/apps/common/rbac.py` |
| Credential encryption | `apps/api/apps/common/crypto.py` |
| Service authentication | `apps/api/apps/common/service_auth.py`, `ai_service/security/internal_auth.py` |
| SQL safety | `apps/ai-service/ai_service/sql/validator.py`, `connections/` |
| SSRF | `apps/api/apps/datasources/validators.py`, `ai_service/security/host_guard.py` |
| Prompt injection | `ai_service/security/injection.py`, `agents/prompts.py` |
| Upload validation | `apps/api/apps/documents/validators.py` |
| Log redaction | `apps/api/apps/common/logging.py` |
| Secret scanning | `scripts/dev/scan_secrets.sh` |

## Testing security changes

```bash
make test-security   # API security suite
make test-ai         # validator, host guard, injection
make security        # static analysis, dependency audit, boundary checks
```

## Reporting a vulnerability

See [SECURITY.md](../../SECURITY.md). Private disclosure only.
