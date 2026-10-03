# Secrets Management

## Principles

1. **No secret in source.** Not in code, tests, fixtures, docs or CI files.
2. **No secret in the image.** Configuration is injected at runtime.
3. **Least privilege.** The AI service holds one secret (the internal service
   token) and no database credentials of its own.
4. **Rotatable.** Every secret can be replaced by changing an environment value
   and restarting, with one documented exception (the Fernet key).

## Generation

```bash
# Django secret key
python -c "import secrets; print(secrets.token_urlsafe(48))"

# Fernet key (data-source credential encryption)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Internal service token
python -c "import secrets; print(secrets.token_urlsafe(40))"
```

## Storage

| Environment | Mechanism |
| ----------- | --------- |
| Local | `.env` (git-ignored, created from `.env.example`) |
| CI | Repository/environment secrets |
| Production | **Recommended:** a managed secret store injected as environment variables. Not yet implemented — see below. |

## Handling rules

- Never paste a secret into an issue, PR, chat or log.
- Never add a secret to `packages/`, `database/` fixtures or test files. Tests use
  deterministic non-secret keys (`config/settings/test.py`).
- Rotate immediately if a secret may have been exposed, then check the audit log
  for `datasource.credential_accessed` and `auth.login` around the exposure window.

## Rotation

| Secret | Procedure | Impact |
| ------ | --------- | ------ |
| `DJANGO_SECRET_KEY` | Replace and restart the API | All JWTs and sessions invalidated; users sign in again |
| `INTERNAL_SERVICE_TOKEN` | Replace on **both** API and AI service, then restart both | Brief window where internal calls fail; deploy together |
| LLM / embedding keys | Replace at the provider, update env, restart the AI service | In-flight AI runs fail |
| `DATAFORGE_FERNET_KEY` | **Requires re-encryption.** See below | Stored data-source passwords become unreadable if lost |
| Data-source password | Edit the data source in the UI | None |

### Fernet key rotation (manual)

There is no automatic re-encryption. The supported procedure is:

1. Decrypt every `DataSource.password_encrypted` with the old key and re-encrypt
   with the new key (a management command is **not** yet provided).
2. Replace `DATAFORGE_FERNET_KEY` and restart.

Until that command exists, treat the Fernet key as unrotatable without a
maintenance window. This is a tracked gap.

## Detection

`scripts/dev/scan_secrets.sh` runs in CI (`.github/workflows/security.yml`). It
scans tracked files for AWS keys, OpenAI/Anthropic keys, GitHub/GitLab tokens,
Slack tokens, private key headers, and a tracked `.env` file.

## Gaps

- No managed vault, no dynamic credentials, no per-secret audit trail.
- No automated Fernet re-encryption command.
- No scheduled rotation policy.
