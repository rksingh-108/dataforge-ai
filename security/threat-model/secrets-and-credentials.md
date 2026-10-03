# Threat model — Secrets and customer credentials

## Assets

| Secret | Where it lives | Blast radius if leaked |
| ------ | -------------- | ---------------------- |
| `DJANGO_SECRET_KEY` | Environment only | JWT forgery, session compromise |
| `DATAFORGE_FERNET_KEY` | Environment only | Decryption of every stored data-source password |
| `INTERNAL_SERVICE_TOKEN` | Environment only | Ability to call internal endpoints as the platform |
| LLM / embedding API keys | Environment only | Cost abuse, data exposure to the vendor |
| Data-source passwords | Database, Fernet-encrypted | Read access to a customer database |
| User passwords | Database, Django hashes | Account takeover |

## Threats and controls

| # | Threat | Control |
| - | ------ | ------- |
| T1 | Secret committed to git | `.gitignore` excludes `.env*` (except `.env.example`); `scripts/dev/scan_secrets.sh` scans tracked files for high-signal patterns in CI |
| T2 | Secret in a log line | `RedactingFormatter` scrubs `password`, `secret`, `token`, `api_key`, bearer tokens and `postgres://` URLs from every rendered record; the API's exception handler returns generic messages for 500s |
| T3 | Secret in an API response | Data-source password fields are write-only; read serializers omit them; the AI service's connection endpoint is not part of the public API and is audited on every call |
| T4 | Secret in an AI prompt | The model never receives credentials: connection settings are fetched by the tool process and kept out of messages; trace summaries are redacted |
| T5 | Weak password | Django validators (min length 10, common-password and numeric checks) enforced at the API layer |
| T6 | Reversible storage of a customer password | Fernet (AES-128-CBC + HMAC) with an environment key; authenticated decryption fails closed on tampering |
| T7 | Internal call forgery | Constant-time comparison of the service token (`hmac.compare_digest`); internal routes are not publicly routed |
| T8 | Over-broad credentials | Data sources default to `is_read_only=True`; the AI service opens read-only sessions; connection testing uses the same account |
| T9 | Stale credentials after offboarding | Rotate via `.env` and restart; `DATAFORGE_FERNET_KEY` rotation requires re-encrypting stored passwords (see `secrets-management/`) |

## Verified by

- `apps/api/apps/common/tests/test_crypto.py` — round-trip, tamper detection, missing key.
- `apps/api/apps/datasources/tests/test_datasources.py` — password encrypted at rest and never serialized.
- `apps/api/apps/ai_bridge/tests/test_internal_endpoints.py` — token required, org scoped, access audited.
- `scripts/dev/scan_secrets.sh` — no credentials in tracked files.

## Residual risk

- Secrets are environment variables, not a managed vault. There is no rotation
  automation and no per-secret access audit. A secrets manager (Vault, AWS Secrets
  Manager, etc.) is the recommended evolution and is tracked in
  [`../secrets-management/README.md`](../secrets-management/README.md).
- Fernet key rotation is manual and, if the key is lost, stored data-source
  passwords must be re-entered. This is documented as an operational constraint.
