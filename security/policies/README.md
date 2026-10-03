# Security Policies

Short, enforceable rules. Each one exists because violating it has a real
consequence in this system. If a rule cannot be enforced by tooling or review, it
is not listed here.

## P1 — Never commit a secret

Not in code, tests, fixtures, docs, CI files or commit messages. Configuration is
injected at runtime. Enforced by `.gitignore` and
`scripts/dev/scan_secrets.sh` (runs in CI).

## P2 — Authorization is server-side, always

Add a DRF permission class. Never decide access in a view body, and never treat a
hidden UI element as a control. Enforced by review and by
`apps/api/tests/security/test_authorization_matrix.py`.

## P3 — Every tenant query is scoped

Reads go through a selector that filters on `organization_id` (or the internal
endpoint's validated `X-DataForge-Org`). New tenant models inherit
`OrganizationScopedModel`. Enforced by review and
`apps/api/tests/security/test_tenant_isolation.py`.

## P4 — Untrusted SQL never executes as written

Model-authored SQL passes `validate_read_only_query` before execution, and the
session is read-only. Enforced by
`apps/ai-service/tests/test_sql_validator.py`.

## P5 — The model never holds a credential

Credentials stay in the platform and are fetched by the tool process, never
placed in a prompt. Enforced by review and by the redaction rules in
`apps/api/apps/common/logging.py` and `orchestrator._summarise_arguments`.

## P6 — Validate outbound hosts before connecting

Every user-supplied host passes `assert_host_allowed` at create time **and** at
connect time. Enforced by both test suites.

## P7 — Uploads are validated by content, not by name

Extension, declared type, magic bytes, size and checksum. Enforced by
`apps/api/apps/documents/tests/test_documents.py`.

## P8 — Audit events are append-only

`AuditLog` raises on update and delete. Do not add a write path to it. Enforced by
`test_audit_log_is_append_only`.

## P9 — A security fix ships with a regression test

The test must fail before the fix. No exceptions; no `@pytest.mark.skip`.

## P10 — Errors do not leak internals

Clients receive a stable error envelope with a code and a request id. Stack traces
and driver messages stay in the logs. Enforced by
`apps/api/apps/common/exceptions.py` and review.

## P11 — Dependency additions are reviewed

New dependencies require an owner for security updates. Run `pip-audit` /
`npm audit` before adding. A new dependency in `apps/api` requires a backend
review; in `apps/ai-service`, an AI + security review.

## P12 — No custom cryptography

Use `cryptography`, Django's hashers and `djangorestframework-simplejwt`. Writing
your own cipher, token format or comparison function is prohibited.

## Privacy

- Do not put real customer data into fixtures, seeds or tests. The seed command
  creates a synthetic organization only, and only when `DEBUG=True`.
- Document content is sent to the configured LLM provider as prompt context. This
  is a product decision; organizations must be informed. Provider data-handling
  terms are an operational responsibility, not enforced by code.
