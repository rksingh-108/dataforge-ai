# Security Tests

The security suites are deliberately placed **next to the code they protect**, so
a developer sees the failing test before they change the control. This directory
exists to point at them and to hold any test that genuinely spans services.

## Where the suites are

| Suite | Location | What it proves |
| ----- | -------- | -------------- |
| Tenant isolation | `apps/api/tests/security/test_tenant_isolation.py` | No cross-organization access through any surface |
| Authorization matrix | `apps/api/tests/security/test_authorization_matrix.py` | Each role is denied exactly what it should be |
| Security headers | `apps/api/tests/security/test_security_headers.py` | Hardening headers are actually sent |
| Throttling | `apps/api/tests/security/test_rate_limiting.py` | Login and analyst endpoints are throttled |
| SQL safety | `apps/ai-service/tests/test_sql_validator.py` | 29 adversarial SQL cases are rejected |
| Host guard / injection | `apps/ai-service/tests/test_security.py` | SSRF targets rejected; injection flagged |
| Tool scoping | `apps/ai-service/tests/test_tools.py` | Tools refuse out-of-scope datasources |
| Credential handling | `apps/api/apps/*/tests/` | Encrypted at rest, never serialized, access audited |
| Upload validation | `apps/api/apps/documents/tests/test_documents.py` | Spoofed/malformed uploads rejected |

## Running

```bash
make test-security    # apps/api/tests/security
make test-ai          # includes validator, host guard, injection
make security         # static analysis, dependency audit, boundary checks, secret scan
```

All of the above run in `.github/workflows/security.yml`.

## Rules for adding a security test

1. **Name it after the attack**, not the fix:
   `test_service_cannot_reach_another_tenant_datasource`.
2. **Make it fail first.** Include the failing output in the PR description.
3. **Assert the security property**, not an implementation detail.
4. **Do not stub the control under test.** Stubbing the validator proves nothing
   about the validator.
5. **Register it** in this table and in
   [`security/security-testing/README.md`](../../security/security-testing/README.md).

## Cross-service tests here

A test belongs in this directory only if it needs more than one service running and
is security-shaped — for example, asserting that the AI service cannot obtain
another tenant's credentials over HTTP with a valid service token. The component
tests already cover the same property in-process; a live test would additionally
catch transport-level mistakes (wrong header name, wrong scope value).
