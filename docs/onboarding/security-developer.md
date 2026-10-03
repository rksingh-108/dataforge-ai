# Onboarding — Security Developer

## Your area

**You own:** `security/`, `tests/security/`, and the security-critical code paths
called out in [`.github/CODEOWNERS`](../../.github/CODEOWNERS):

- `apps/api/apps/common/` (RBAC, permissions, crypto, service auth)
- `apps/api/apps/accounts/`, `apps/api/apps/organizations/`
- `apps/ai-service/ai_service/sql/`, `/security/`, `/connections/`

You are a required reviewer for any change touching authentication,
authorization, tenancy, credentials, outbound network calls or AI tool execution.

## Start here

1. [security/README.md](../../security/README.md) — the control map. Every row
   names the test that proves it.
2. [security/threat-model/](../../security/threat-model/) — seven models, one per
   trust boundary.
3. [security/policies/README.md](../../security/policies/README.md) — twelve rules.
4. [security/vulnerability-management/README.md](../../security/vulnerability-management/README.md)
   — eleven open items with owners. **Read this before promising anyone anything.**

## Local setup

```bash
make security                    # boundary checks, bandit, pip-audit, secret scan, Django --deploy
make test-security               # the API security suite
make test-ai                     # includes validator, host guard, injection tests
```

`make security` needs both virtualenvs (`.venv` and `.venv-ai`).

## How we work

### Claim nothing that is not tested

This is the culture here. Before you tell anyone a control exists, name the test.
If there is no test, the honest statement is "not verified".

### Findings get a regression test first

1. Reproduce with a failing test named after the attack.
2. Fix it.
3. Show both in the PR: the test failing before, passing after.
4. Add or update the control row in `security/README.md`.
5. If it was a gap in a threat model, update the model in the same PR.

### Where security work belongs

| Kind of finding | Where the fix goes |
| --------------- | ------------------ |
| Cross-tenant access | `apps/api/.../permissions.py` + selectors + a tenant test |
| Missing permission | `apps/api/.../rbac.py` + the authorization matrix test |
| SQL validator bypass | `ai_service/sql/validator.py` + a case in `test_sql_validator.py` |
| SSRF | `datasources/validators.py` **and** `ai_service/security/host_guard.py` |
| Injection behaviour | `ai_service/security/injection.py` + the structural control that actually prevents harm |
| Credential handling | `apps/api/apps/common/crypto.py`, serializers, audit |
| Config/hardening | `config/settings/production.py`, `scripts/dev/run-security-checks.sh` |
| CI coverage | `.github/workflows/security.yml` |

## Reviewing a PR as security

Ask in this order:

1. **Tenancy.** Does every new query filter by organization? Does a non-member get
   404?
2. **Authorization.** Does the endpoint declare a permission? Is the permission the
   narrowest one that works?
3. **Secrets.** Any credential in a response, a log line, a prompt, a test fixture
   or a commit? (Search the diff for the word "password".)
4. **Outbound calls.** New network destination? Does it pass the host guard?
5. **Model trust.** Does any new code treat model output as authoritative?
6. **Uploads.** New file type or parser? Is it validated by content?
7. **Audit.** Is the new action recorded, and does it avoid storing sensitive data?
8. **Tests.** Do they fail without the change? Are they named after the attack?

## Your first tasks

- Add a case to `test_sql_validator.py` for a bypass you can construct.
- Add the missing WebSocket membership-check test (VM-9).
- Add a CSP header with nonces (VM-3).
- Write the Fernet re-encryption command (VM-6).

## Escalation

Follow [security/incident-response/README.md](../../security/incident-response/README.md).
For an active incident: contain first (rotate the secret, disable the tool, scale
down the AI service), diagnose second. Preserve audit records before changing
anything.
