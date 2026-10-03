# Threat model — Multi-tenancy

## Scope

Separation between organizations. This is the highest-severity class of bug in
DataForge AI: a leak here breaks every customer at once.

## The invariant

> Every read and write of tenant-owned data is scoped by an organization the
> caller has been **proven** to be a member of, and the proof happens server-side
> on every request.

## Enforcement layers

1. **Schema.** Every tenant-owned model inherits `OrganizationScopedModel`
   (`apps/api/apps/common/models.py`), so the organization column cannot be
   forgotten. `DocumentChunk` also carries a denormalized `organization` so vector
   search can be filtered without a join.
2. **Permission resolution.** `OrganizationAccess.get_membership` resolves the
   caller's active membership from the URL's `org_id` — and **only** from there;
   the client-controlled `X-Organization-Id` header is ignored — and attaches it
   to the request. Views obtain the tenant through `require_organization(request)`
   and `require_permission(...)` then checks the role's permission.
   `apps/api/apps/common/permissions.py`.
3. **Query scoping.** Views never build querysets on tenant models directly; they
   call selectors that filter on `organization_id` taken from the resolved
   membership. `apps/*/selectors.py`.
4. **Response to non-members.** Object routes return **404**, not 403, so the
   existence of another tenant's resource is not disclosed.
5. **Internal service calls.** The AI service must send `X-DataForge-Org` together
   with the shared service token, and the API validates both before returning
   anything; the AI service cannot widen scope because scope is a service-level
   declaration, never model output. This is a distinct, service-authenticated
   header — not the user-facing `X-Organization-Id`, which is banned.

## Threats and controls

| # | Threat | Control | Verified by |
| - | ------ | ------- | ----------- |
| T1 | Read another org's data source by guessing its UUID | `get_datasource` filters on both id and org; non-members get 404 | `test_datasource_is_tenant_isolated` |
| T2 | List another org's documents | Selector filters by org from membership | `test_documents_are_tenant_isolated` |
| T3 | Retrieve another org's vector chunks | `search_chunks` filters `organization_id` in the SQL | `test_search_is_tenant_scoped`, `test_document_search_is_tenant_scoped` |
| T4 | View another org's executions or audit logs | Selectors filter by org; permission classes gate the route | `test_execution_list_is_tenant_scoped`, `test_analyst_cannot_read_audit_logs` |
| T5 | Ask the AI to query a foreign data source | AI service only receives ids the API verified; tools re-check | `test_datasource_ids_are_filtered_to_owned_ones`, `test_tools_reject_out_of_scope_datasource` |
| T6 | Fetch another org's credentials via the internal endpoint | Service token + `X-DataForge-Org` validated, datasource looked up within that org | `test_service_cannot_reach_another_tenant_datasource` |
| T7 | Subscribe to another org's realtime channel | WebSocket consumer re-checks membership at connect time; 4401/4403 on failure | `apps/api/apps/realtime/tests/test_websocket_auth.py` |
| T9 | Switch tenant by forging `X-Organization-Id`, a body or query org id | Header ignored; scope derives only from URL `org_id` → verified membership; structural guard bans client-controlled scope | `test_tenant_scope_resolution.py`, `scripts/dev/check_boundaries.py` |
| T8 | Tamper with the org cookie to widen access | Cookie is advisory; every request is re-authorized server-side | `apps/web/app/api/session/org/route.ts` validates against `/me/` |

## Residual risk

- **Query-level mistakes.** A future selector that forgets the filter is the
  realistic failure mode. Mitigation: the selector pattern, code review via
  `CODEOWNERS` on `apps/api`, the tenant-isolation test suite, and a structural
  guard (`scripts/dev/check_boundaries.py`) that rejects reading the
  client-controlled `X-Organization-Id` header or building scope from client
  input. A *compiler-level* default manager that raises when unscoped is not
  implemented — tracked as VM-8 in
  [`../vulnerability-management/README.md`](../vulnerability-management/README.md).
- **Analytics/aggregation paths.** `InsightsView` aggregates with an explicit
  `organization_id` filter; new aggregates must do the same and are covered by
  `test_insights_reports_real_aggregates`.
