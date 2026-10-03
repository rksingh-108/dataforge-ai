# Operations Runbook

Day-two operations for a running DataForge AI deployment. Every command assumes
the deployment uses the container names from `docker-compose.yml`; adapt to your
orchestrator.

## Health

```bash
curl -fsS http://localhost:8000/_health/ | jq   # database + redis
curl -fsS http://localhost:8001/_health/ | jq   # config + provider names (never keys)
docker compose ps
```

`/_health/` performs **real** dependency checks and returns 503 when a required
dependency is unreachable. A 200 means the service can serve traffic.

## Routine tasks

| Task | Command |
| ---- | ------- |
| Tail logs | `docker compose logs -f --tail=100` |
| Follow one request | `docker compose logs api ai-service web worker \| grep <request-id>` |
| Apply migrations | `docker compose exec api python manage.py migrate` |
| Django shell | `docker compose exec api python manage.py shell` |
| Queue depth | `docker compose exec redis redis-cli -n 1 llen celery` |
| Worker liveness | `docker compose logs worker --tail=50` |
| Restart one service | `docker compose restart ai-service` |
| Reload config | edit `.env`, then `docker compose up -d <service>` |

## Common incidents

### API returns 503 on `/_health/`

Check `checks` in the response.

- `database: unreachable` → Postgres down or credentials wrong. `docker compose ps db`, then `docker compose logs db`.
- `redis: unreachable` → Redis down. `docker compose ps redis`, `docker compose exec redis redis-cli ping`.

The API will still serve requests that do not need the failing dependency, but
migrations and background work will not.

### Analyst runs all fail with `upstream_error`

The API cannot reach the AI service.

1. `curl -fsS http://localhost:8001/_health/`.
2. Check that `INTERNAL_SERVICE_TOKEN` is identical on **both** api and ai-service.
   A mismatch is the most common cause and presents as a 401 from the AI service.
3. Check `AI_SERVICE_URL` resolves inside the network (`http://ai-service:8001`).

### Analyst runs all fail with `provider_error`

The AI service reached the vendor and the vendor refused.

1. `curl -fsS http://localhost:8001/_health/ | jq .checks` — is the provider/model correct?
2. Verify `LLM_API_KEY` and `LLM_BASE_URL`.
3. Check the vendor for rate limits or an exhausted quota.
4. Inspect a failed execution: it is recorded in history with a redacted reason.

### Documents stuck in `processing`

1. Is the worker alive? `docker compose logs worker --tail=50`.
2. Is the queue backing up? `redis-cli -n 1 llen celery`.
3. Do api and worker share the `media` volume? (They must — the worker reads the file.)
4. If the task exhausted its retries, the document is marked `failed` with a reason;
   re-queue with `POST /api/v1/orgs/{org}/documents/{id}/reprocess/`.

### Login fails for everyone

The most likely cause is a rotated `DJANGO_SECRET_KEY`, which invalidates every
token — or a corrupted `rest_framework_simplejwt.token_blacklist` table.

```bash
docker compose exec api python manage.py shell -c "
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
print(OutstandingToken.objects.count())"
```

### Users report "resource not found" on a resource they can see

Almost always correct behaviour: they are not a member of the organization in the
URL. Verify:

```bash
docker compose exec api python manage.py shell -c "
from apps.organizations.models import Membership
for m in Membership.objects.select_related('user','organization').filter(is_active=True)[:20]:
    print(m.user.email, m.organization.slug, m.role)"
```

## Credential and key rotation

| Secret | Procedure | Effect |
| ------ | --------- | ------ |
| `INTERNAL_SERVICE_TOKEN` | Update on **both** services, restart together | Brief internal-call failures if not simultaneous |
| `DJANGO_SECRET_KEY` | Replace, restart api | All sessions invalidated |
| LLM/embedding keys | Replace at the vendor, update env, restart ai-service | In-flight AI runs fail |
| Data-source password | Edit the data source in the UI | None |
| `DATAFORGE_FERNET_KEY` | **Not rotatable** without a re-encryption step — see [secrets-management](../security/secrets-management/README.md) and VM-6 | Stored credentials unreadable if lost |

## Backup and restore

Backups must cover **both** persistent stores:

- `db_data` — PostgreSQL (platform data, schema, audit log)
- `media` — uploaded documents

```bash
docker compose exec -T db pg_dump -U dataforge dataforge | gzip > backup-$(date +%F).sql.gz
docker compose run --rm -v "$PWD:/backup" api sh -c "tar czf /backup/media-$(date +%F).tgz -C /app media"
```

Restore (into a **new** database first; never restore over live data without a
plan):

```bash
gunzip -c backup-2026-10-03.sql.gz | docker compose exec -T db psql -U dataforge -d dataforge_restore
```

Retention policy is **not implemented** (D2). Audit logs are append-only and are
retained indefinitely.

## Scaling notes

- **api**: scales horizontally; stateless apart from the shared database.
- **worker**: scales horizontally; both api and worker need the `media` volume, so
  a multi-host deployment needs shared object storage instead of a local volume.
- **ai-service**: scales horizontally; it holds no state. It is the egress point,
  so scaling it multiplies outbound capability — keep its network egress restricted.
- **Database**: no read replica or pooler is configured (D4). Add PgBouncer before
  running many API replicas.

## Maintenance windows

Changing `DATAFORGE_FERNET_KEY` requires re-encrypting every stored password and
therefore a maintenance window until VM-6 is closed. Changing `EMBEDDING_DIM`
requires a migration plus re-embedding every chunk — treat it as a project.

## Escalation

| Situation | Where |
| --------- | ----- |
| Suspected security incident | [security/incident-response/README.md](../../security/incident-response/README.md) |
| Data loss or corruption | Stop writes; preserve the database volume; escalate to the data owner |
| Unknown outage | Capture `docker compose ps`, `/_health/` output and recent logs **before** restarting — restarting destroys evidence |
