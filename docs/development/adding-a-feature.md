# Adding a Feature

A worked example: **add a "notes" field to data sources**. Follow the same shape
for anything bigger; the order is what matters.

## 0. Before writing code

- Open an issue. Agree on scope and acceptance criteria in writing.
- Identify the owning area(s) from
  [service-boundaries.md](../architecture/service-boundaries.md).
- Decide whether it crosses a trust boundary (auth, tenancy, credentials,
  outbound network, SQL). If so, plan the security review now, not at the end.

## 1. Branch

```bash
git switch main && git pull
git switch -c feat/datasource-notes
```

## 2. Model and migration

```python
# apps/api/apps/datasources/models.py
class DataSource(OrganizationScopedModel):
    ...
    notes = models.TextField(blank=True)
```

```bash
cd apps/api
python manage.py makemigrations datasources
python manage.py migrate
```

Commit the migration with the model change — never separately.

## 3. Services and selectors

Business rules go in services; reads go in selectors. For a trivial field, no
service change is needed; for a rule (e.g. "notes are capped at 2000 characters")
it goes in the service, with a test.

## 4. Serializers

```python
class DataSourceUpdateSerializer(serializers.Serializer):
    notes = serializers.CharField(max_length=2000, required=False, allow_blank=True)
```

Never expose credentials. Never put business rules in a serializer beyond shape.

## 5. View and permissions

```python
class DataSourceDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [require_permission(Permission.DATASOURCE_MANAGE)]
```

If the feature needs a **new permission**, add it to `rbac.py`, add a row to the
authorization matrix test, and update
[`security/access-control/README.md`](../../security/access-control/README.md).

## 6. Tests

```python
def test_updating_notes_is_audited(auth_client, organization):
    ...
```

At minimum: a happy path, an authorization failure, and a tenant-isolation check
if the resource is tenant-owned. Run:

```bash
make test-backend
```

## 7. API contract

Update `packages/api-contracts/` so other teams and the frontend can rely on the
shape.

## 8. Frontend

1. Add the field to `apps/web/lib/types.ts`.
2. Use `clientFetch` from a client component (or `apiFetch` from a server
   component) — never call the API host directly.
3. Gate any UI affordance with `lib/permissions.ts` **for rendering only**.
4. Provide loading, empty and error states.

```bash
cd apps/web && npm run typecheck && npm run test && npm run build
```

## 9. Documentation

- Update the relevant doc under `docs/`.
- Add a `CHANGELOG.md` entry under `Unreleased`.
- If behaviour is deliberately incomplete, add it to
  [known-limitations.md](known-limitations.md) rather than leaving it implied.

## 10. Verify like CI

```bash
make ci          # boundary checks, all tests, lint
make security    # static analysis, dependency audit
```

## 11. Pull request

Open it early as a draft. Fill in the PR template honestly — especially the
Definition of Done and security review sections.

## Definition of Done

A change is done when **all** of these hold:

1. Acceptance criteria from the issue are met.
2. Tests exist, are meaningful, and fail without the change.
3. `make ci` passes locally.
4. Documentation is updated in the same PR.
5. The API contract is updated if the API changed.
6. No secrets, no real customer data, no new `# noqa`/`skip` without justification.
7. Tenant isolation and authorization are explicitly considered.
8. Required reviews (CODEOWNERS) have approved.
9. CI is green and the branch is up to date with `main`.
10. Any deliberate limitation is documented where a reader would look for it.
