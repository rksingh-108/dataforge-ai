# Onboarding — Backend Developer

## Your area

**You own:** `apps/api` — the domain, the API surface, authorization, tenancy and
the platform database schema.

**You do not own:** LLM/agent logic (`apps/ai-service`), UI (`apps/web`).

## Set up

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r apps/api/requirements/dev.txt
docker compose up -d db redis
cd apps/api && python manage.py migrate && python manage.py seed_development
python manage.py runserver
```

Use `daphne config.asgi:application` when working on WebSockets.

## The layering (this is the job)

```
views/         authorization + delegation. No ORM writes, no business rules.
serializers/   shape and field validation only.
services/      writes and invariants, in transactions.
selectors/     reads, always tenant-scoped.
models/        schema and constraints.
permissions.py the only place that answers "may this caller do this?".
```

A PR that puts a business rule in a serializer, or an ORM query in a view, will be
sent back. This is not pedantry: it is how tenancy and authorization stay
auditable.

## Apps and what they own

| App | Responsibility |
| --- | -------------- |
| `common` | Base models, RBAC matrix, permission classes, crypto, exceptions, health, WS auth, service auth |
| `accounts` | User model, login/logout/refresh, password change, `/me/` |
| `organizations` | Organizations, memberships, roles, last-owner invariant |
| `datasources` | Connection records, credential encryption, connection tests, schema cache |
| `documents` | Upload validation, documents, vector chunks, Celery processing task |
| `analytics` | Executions, execution steps, append-only audit log, insights |
| `ai_bridge` | The HTTP client to the AI service + public analyst endpoint + internal endpoints |
| `realtime` | WebSocket consumer and broadcast helper |

## Non-negotiables

1. **Tenant isolation.** New tenant models inherit `OrganizationScopedModel`.
   Every query filters by organization. See
   [authorization-model.md](../architecture/authorization-model.md).
2. **Authorization in permission classes.** Use `require_permission`. Never decide
   access in a view body.
3. **Non-members get 404**, not 403.
4. **`AuditLog` is append-only.** Never add a write path.
5. **No credentials in responses or logs.** Passwords are write-only and
   Fernet-encrypted at rest.
6. **Views do not call the AI service directly.** Go through `ai_bridge`.

## Adding an endpoint — the shape

```python
class WidgetListView(generics.ListCreateAPIView):
    serializer_class = WidgetSerializer
    permission_classes = [require_permission(Permission.WIDGET_VIEW)]

    def get_permissions(self):
        if self.request.method == "POST":
            return [require_permission(Permission.WIDGET_MANAGE)()]
        return super().get_permissions()

    def get_queryset(self):
        return widget_selectors.list_widgets(organization_id=self.kwargs["org_id"])

    def create(self, request, *args, **kwargs):
        payload = WidgetCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        widget = widget_services.create_widget(
            organization=request.membership.organization,
            actor=request.user,
            **payload.validated_data,
        )
        return Response(WidgetSerializer(widget).data, status=201)
```

## Testing

```bash
make test-backend          # spins up a throwaway Postgres+pgvector
```

Use the fixtures in `apps/api/conftest.py` (`organization`, `auth_client`,
`make_member`, `client_for`). Authenticate with real JWTs, not
`force_authenticate`, unless you are testing something unrelated to auth.

For every new endpoint, add: a happy path, an authorization failure, and a
tenant-isolation check if the resource is tenant-owned.

## Migrations

```bash
python manage.py makemigrations <app>
python manage.py migrate
```

Commit the migration with the model change. Review the generated SQL for indexes
and constraints. Every tenant-owned table needs an organization index; every
lookup path you rely on needs an index.

## Good first tasks

- Add an authorization test for an endpoint that lacks one.
- Add a missing index with a migration and a short justification.
- Improve an error message using a domain exception instead of a bare `Exception`.
- Document a service function that lacks a docstring.

## Ask about

- Anything touching tenancy, authorization or credentials → security owner.
- Anything where you are tempted to put AI logic in the API → AI owner. It belongs
  in the AI service.
