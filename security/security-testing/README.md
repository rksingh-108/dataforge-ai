# Security Testing

Security tests live next to the code they protect, plus a cross-cutting suite:

| Suite | Location | What it proves |
| ----- | -------- | -------------- |
| Tenant isolation | `apps/api/tests/security/test_tenant_isolation.py` | No cross-organization read/write through the API |
| Tenant scope resolution | `apps/api/tests/security/test_tenant_scope_resolution.py` | Forged `X-Organization-Id`, URL/body/query org ids cannot switch or widen tenant scope (22 cases) |
| WebSocket membership | `apps/api/apps/realtime/tests/test_websocket_auth.py` | Only verified members connect to an org channel; forged org / non-member / bad token rejected (6 cases) |
| Authorization matrix | `apps/api/tests/security/test_authorization_matrix.py` | Every role is denied what it should be denied |
| Security headers | `apps/api/tests/security/test_security_headers.py` | Hardening headers are actually sent |
| Throttling | `apps/api/tests/security/test_rate_limiting.py` | The auth throttle is configured and applies |
| SQL safety | `apps/ai-service/tests/test_sql_validator.py` | 29 adversarial SQL cases are rejected |
| Host guard | `apps/ai-service/tests/test_security.py` | SSRF targets are rejected |
| Prompt injection | `apps/ai-service/tests/test_security.py`, `test_tools.py` | Injection is flagged, not obeyed |
| Credential handling | `apps/api/apps/datasources/tests/`, `apps/api/apps/ai_bridge/tests/` | Secrets are encrypted, never serialized, access audited |
| Upload validation | `apps/api/apps/documents/tests/test_documents.py` | Malformed/oversized/spoofed uploads rejected |

Run them:

```bash
make test-security          # API security suite
make test-ai                # includes validator + host guard + injection
make security               # static analysis, dependency audit, boundary checks
```

CI runs all of the above in `.github/workflows/security.yml`.

## Writing a security test

1. **Name it after the attack**, not the fix: `test_service_cannot_reach_another_tenant_datasource`,
   not `test_org_filter_works`.
2. **Make it fail first.** Demonstrate the vulnerability before fixing it; include
   the failing output in the PR description.
3. **Assert on the security property**, not on an implementation detail. Assert
   "404 for a non-member", not "the selector was called".
4. **Prefer the real component.** Patch only true external boundaries (LLM
   vendors, customer databases). A test that stubs the validator proves nothing
   about the validator.
5. **Add it to this table** so the suite stays discoverable.

## What we deliberately do not do

- **No security claims without a test.** Every control in
  [`../README.md`](../README.md) names its test.
- **No mocked-to-pass tests.** Stubbing the thing under test is a rejected
  pattern in review.
- **No `skip` for a known failure.** A known gap goes in
  [`../vulnerability-management/README.md`](../vulnerability-management/README.md)
  with an owner, not into a skipped test.
