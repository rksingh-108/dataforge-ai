# Authorization Model

## Two questions, answered separately

Every request answers two questions:

1. **Tenancy** — is the caller a member of the organization this request targets?
2. **Permission** — does the caller's role allow this specific action?

Both are answered **server-side, on every request**, from the database — never from
a token claim, a header the client controls, or the frontend.

## Tenancy

```
request ─▶ resolve org id (URL kwarg `org_id` — and only that)
        ─▶ look up active Membership(user, organization)
        ─▶ attach request.membership + request.organization
        ─▶ scope every query through that organization
```

- **The organization id comes from the URL route and nowhere else.** A
  client-supplied `X-Organization-Id` header is deliberately ignored: it is fully
  attacker-controlled, so treating it as a scope source would let a member of one
  tenant read another tenant's data by changing one header. A client that needs a
  different organization addresses it in the path, and the server verifies
  membership before any data is returned.
- Membership must be `is_active=True` and the organization must be active.
- Non-members receive **404**, not 403, for object routes: the existence of
  another tenant's resource is not disclosed. For org-scoped collection routes the
  whole route also returns 404, since the organization id is in the path.
- The comparison is the same either way — a caller learns nothing from the status
  code that they did not already know from the id they supplied.

## Permissions

The matrix lives in `apps/api/apps/common/rbac.py` (see
[`security/access-control/README.md`](../../security/access-control/README.md) for
the table). Roles: `owner`, `admin`, `analyst`, `viewer`.

Unknown roles resolve to **no permissions** (fail closed).

## Enforcement in code

Views declare a permission class; they never decide access inline.

```python
class DataSourceListCreateView(generics.ListCreateAPIView):
    permission_classes = [require_permission(Permission.DATASOURCE_VIEW)]

    def get_permissions(self):
        if self.request.method == "POST":
            return [require_permission(Permission.DATASOURCE_MANAGE)()]
        return super().get_permissions()
```

`require_permission(...)` returns a DRF permission class that:

1. requires an authenticated user,
2. resolves the membership (404 for non-members on org-scoped routes),
3. checks `role_has_permission(membership.role, permission)`.

For views that cannot use a permission class, the sanctioned helper is
`has_organization_permission(request, Permission.X)`.

### Obtaining the tenant (one sanctioned way)

Once the permission class has run, a view or service obtains the tenant through a
single helper — never by re-reading the URL, the body, a query parameter or a
header:

```python
from apps.common.permissions import require_organization

organization = require_organization(request)   # verified membership, or 404
```

`require_organization` returns the organization from the caller's active
membership and raises `NotFound` when there is none, preserving the 404-not-403
convention. Two rules keep this honest, and both are enforced by
`scripts/dev/check_boundaries.py` in CI:

1. `apps/api` must not read `X-Organization-Id`.
2. A call that passes `organization_id` / `organization` / `org_id` must not take
   that value from `kwargs`, `query_params` or `request.data`.

## Data-layer scoping

Selectors are the read side of the domain and are always org-scoped:

```python
def get_datasource(*, organization_id, datasource_id):
    return DataSource.objects.filter(id=datasource_id, organization_id=organization_id).first()
```

Views never build querysets on tenant models directly, so scoping rules live in one
place per domain.

The schema reinforces the model: tenant-owned models inherit
`OrganizationScopedModel`, which makes the organization column impossible to
forget. `DocumentChunk` denormalizes the organization so vector search filters
without a join.

## The AI path

The AI service is **not** an authorization authority. Before calling it, the API:

1. verifies the caller's membership and `analyst.query` permission,
2. filters any client-supplied `datasource_ids` down to those the organization
   actually owns (`ai_bridge/services.py::_authorized_datasource_ids`),
3. sends those ids plus the organization id.

The AI service treats the organization header as an already-authorized scope and
uses it for retrieval scoping only. Its tools assert that a requested
`datasource_id` is in the approved set, so a manipulated model cannot widen scope.

Internal endpoints require the service token **and** a valid `X-DataForge-Org`;
they are not part of the public API.

## Realtime

The WebSocket consumer re-checks membership at connect time and derives the group
name from the verified organization id. A socket is closed with 4401
(unauthenticated) or 4403 (not a member).

## Adding a permission — checklist

1. Add it to `Permission` and to the relevant role sets in `rbac.py`.
2. Use it in the view via `require_permission`.
3. Add a row to `apps/api/tests/security/test_authorization_matrix.py`.
4. Update the matrix in `security/access-control/README.md`.
5. Update `apps/web/lib/permissions.ts` if the UI should reflect it.

## Known limitations

- **No per-resource ACL.** Access is organization + role only. A viewer sees every
  data source in the organization.
- **No delegation or time-bounded roles.**
- **Scoping is guarded, not compiler-enforced.** Every tenant query must pass an
  explicit organization id; the guard is a CI check plus the tenant-isolation and
  tenant-scope-resolution suites (VM-8). It catches the known footguns, but a
  sufficiently novel way of bypassing `require_organization` would still need
  review to catch.
