# Debugging

## Start with the correlation id

Every response carries `X-Request-Id`. The BFF forwards it, the API logs it, and
the AI service propagates it. Given a failing request, grab the id and grep all
three services:

```bash
docker compose logs api | grep <request-id>
docker compose logs ai-service | grep <request-id>
docker compose logs worker | grep <request-id>
```

If the UI showed an error, the same id is in the response envelope
(`error.request_id`) and in the execution detail page.

## Layer by layer

Work outward from where the failure is observable. Each check isolates one hop.

| Check | Command | Tells you |
| ----- | ------- | --------- |
| Containers healthy? | `docker compose ps` | Which service is down |
| API alive? | `curl -s localhost:8000/_health/` | DB and Redis reachability from the API |
| AI service alive? | `curl -s localhost:8001/_health/` | Config readiness (token, provider names) |
| Web alive? | `curl -sI localhost:3000` | Next.js server running |
| Redis reachable? | `docker compose exec redis redis-cli ping` | Broker/channel layer |
| DB reachable? | `docker compose exec db pg_isready -U dataforge` | Postgres |

## Common symptoms

### Login returns 401 and credentials are correct

1. Did the seed run? `docker compose exec api python manage.py seed_development`
2. Is the account active? `is_active` must be true.
3. Check the audit log for `auth.login_failed` — a burst means throttling or a
   wrong password, not a bug.

```bash
docker compose exec api python manage.py shell -c "
from apps.analytics.models import AuditLog
for r in AuditLog.objects.filter(action='auth.login_failed')[:10]: print(r.created_at, r.metadata)"
```

### A request returns 404 that "should" be 200

Likely correct behaviour: non-members get 404 for org-scoped routes, on purpose
(see [authorization-model.md](../architecture/authorization-model.md)). Confirm
the caller's membership:

```bash
docker compose exec api python manage.py shell -c "
from apps.organizations.models import Membership
for m in Membership.objects.select_related('user','organization')[:20]:
    print(m.user.email, m.organization.slug, m.role, m.is_active)"
```

### An AI run fails

1. `GET /_health/` on the AI service — is the provider configured?
2. Look at the execution: the failed `ExecutionStep` records the tool and a
   redacted reason.
3. `provider_error` means the LLM call failed: check `LLM_API_KEY`, `LLM_BASE_URL`,
   and that the model name is valid for the provider.
4. `upstream_error` in the API means the AI service could not be reached at all —
   check `AI_SERVICE_URL` and that both services share the same
   `INTERNAL_SERVICE_TOKEN`.

### Document stuck in `processing`

The Celery worker is the likely culprit.

```bash
docker compose logs worker | tail -50
docker compose exec redis redis-cli -n 1 llen celery   # queued tasks
```

Confirm the worker and API share the same `media` volume (they do in
`docker-compose.yml`) — the worker reads the file the API stored.

### "Hot host is not allowed"

Working as intended for private/loopback/metadata addresses. For a legitimate
private target, set `DATASOURCE_ALLOW_PRIVATE_NETWORKS=true` (a deliberate
deployment decision) — see [ssrf.md](../../security/threat-model/ssrf.md).

### SQL "query rejected by validator"

The rejection reason is recorded on the step and shown in the UI. Common causes:
an unknown table (refresh the data source schema), a system table, a write
statement, too many joins, or a forbidden function.

## Inspecting state

```bash
# Django shell
docker compose exec api python manage.py shell

# Recent executions with their steps
docker compose exec api python manage.py shell -c "
from apps.analytics.models import Execution
for e in Execution.objects.order_by('-created_at')[:5]:
    print(e.id, e.status, e.error[:80]); [print('  ', s.index, s.tool_name, s.status, s.error[:60]) for s in e.steps.all()]"

# Find a user's memberships
docker compose exec api python manage.py shell -c "
from django.contrib.auth import get_user_model
u = get_user_model().objects.get(email='analyst@dataforge.local')
print([(m.organization.slug, m.role) for m in u.memberships.all()])"
```

## Debugging the frontend

- Server-side errors appear in the `web` container logs, not the browser console.
- `API_BASE_URL` is read at **request** time in the BFF; changing it requires a
  container restart.
- If every proxied call returns 401, the refresh flow failed — check the `web`
  logs for the upstream status from `/api/v1/auth/refresh/`.

## When to stop debugging and ask

If you have spent more than ~30 minutes on a failure that crosses a service
boundary, say so in the team channel with the request id and what you have ruled
out. Cross-service failures are usually a configuration mismatch, and a second
pair of eyes is faster than more logs.
