# API Reference (v1)

Base path: `/api/v1/`. All responses are JSON. Authenticated endpoints require
`Authorization: Bearer <access_token>`.

## Conventions

### Errors

Every error uses one envelope:

```json
{
  "error": {
    "code": "invalid_credentials",
    "message": "Invalid email or password.",
    "details": {},
    "request_id": "0f1c…"
  }
}
```

| Code | HTTP | Meaning |
| ---- | ---- | ------- |
| `invalid_credentials` | 401 | Login failed |
| `not_authenticated` | 401 | Missing/expired token |
| `permission_denied` | 403 | Authenticated but the role does not allow it |
| `not_found` | 404 | Missing **or not a member** (deliberately indistinguishable) |
| `conflict` | 409 | Business-rule conflict (duplicate, last owner) |
| `datasource_unreachable` | 422 | Connection test failed |
| `upstream_error` | 502 | AI service failed |
| `throttled` | 429 | Rate limited |
| `internal_error` | 500 | Unexpected; details are in the logs, not the response |

### Pagination

List endpoints return:

```json
{ "count": 42, "page": 1, "page_size": 25, "total_pages": 2, "results": [] }
```

Query parameters: `page`, `page_size` (max 100). Some list endpoints (organizations,
members, schema) are unpaginated and return a bare array.

### Scoping

Organization-scoped resources are nested: `/api/v1/orgs/{org_id}/...`. The caller's
active membership in `{org_id}` is resolved on every request; a non-member receives
**404**.

## Authentication

| Method | Path | Auth | Body | Returns |
| ------ | ---- | ---- | ---- | ------- |
| POST | `/auth/login/` | none (throttled) | `{email, password}` | `{access, refresh, user, memberships}` |
| POST | `/auth/refresh/` | refresh token | `{refresh}` | `{access, refresh}` |
| POST | `/auth/logout/` | access | `{refresh}` | 205 |
| POST | `/auth/verify/` | — | `{token}` | 200 |
| POST | `/auth/password/change/` | access | `{current_password, new_password}` | `{revoked_refresh_tokens}` |
| GET | `/me/` | access | — | `{user, memberships[], is_staff}` |

## Organizations and members

| Method | Path | Permission | Notes |
| ------ | ---- | ---------- | ----- |
| GET | `/orgs/` | authenticated | Organizations you belong to |
| POST | `/orgs/` | authenticated | Creates an organization; you become owner |
| GET | `/orgs/{org_id}/` | member | |
| GET | `/orgs/{org_id}/members/` | member | |
| POST | `/orgs/{org_id}/members/` | `member.manage` | `{email, role}` — user must exist |
| PATCH | `/orgs/{org_id}/members/{id}/` | `member.manage` | `{role}`; last owner is protected |
| DELETE | `/orgs/{org_id}/members/{id}/` | `member.manage` | Deactivates; last owner is protected |

Valid roles: `owner`, `admin`, `analyst`, `viewer`. Unknown roles grant nothing.

## Data sources

| Method | Path | Permission |
| ------ | ---- | ---------- |
| GET | `/orgs/{org_id}/datasources/` | `datasource.view` |
| POST | `/orgs/{org_id}/datasources/` | `datasource.manage` |
| GET | `/orgs/{org_id}/datasources/{id}/` | `datasource.view` |
| PATCH | `/orgs/{org_id}/datasources/{id}/` | `datasource.manage` |
| DELETE | `/orgs/{org_id}/datasources/{id}/` | `datasource.manage` |
| POST | `/orgs/{org_id}/datasources/{id}/test/` | `datasource.manage` |
| GET | `/orgs/{org_id}/datasources/{id}/schema/` | `datasource.view` |
| POST | `/orgs/{org_id}/datasources/{id}/sync/` | `datasource.manage` |

Create body:

```json
{
  "name": "Warehouse",
  "engine": "postgresql",
  "host": "db.example.com",
  "port": 5432,
  "database_name": "analytics",
  "username": "readonly",
  "password": "…",
  "ssl_mode": "prefer",
  "description": "Optional"
}
```

**The password is write-only.** It is never returned in any response, in any
serializer, on any endpoint. `PATCH` accepts `password` only to change it.

`POST .../test/` returns `{ok, server_version, error}` and updates the data source
status. Hosts in private, loopback or link-local ranges are rejected with 400
unless the deployment opts in.

## Documents

| Method | Path | Permission | Notes |
| ------ | ---- | ---------- | ----- |
| GET | `/orgs/{org_id}/documents/` | `document.view` | Filter with `?status=` |
| POST | `/orgs/{org_id}/documents/` | `document.manage` | `multipart/form-data`, field `file` |
| GET | `/orgs/{org_id}/documents/{id}/` | `document.view` | |
| DELETE | `/orgs/{org_id}/documents/{id}/` | `document.manage` | |
| POST | `/orgs/{org_id}/documents/{id}/reprocess/` | `document.manage` | Re-queues processing |

Accepted types: PDF, DOCX, TXT. Validated by extension, declared content type,
magic bytes and size. A duplicate checksum within the organization returns 409.

Upload returns 201 immediately; processing is asynchronous. Poll the document (or
the executions list) for `status: ready`.

## Analyst

| Method | Path | Permission |
| ------ | ---- | ---------- |
| POST | `/orgs/{org_id}/analyst/query/` | `analyst.query` (throttled `analyst`) |

```json
{
  "question": "How many orders were placed last month?",
  "datasource_ids": ["…"],
  "use_documents": true
}
```

`datasource_ids` are filtered server-side to those the organization owns; unknown
ids are ignored, not trusted. Returns 201 with the resulting execution, including
its steps, answer, provider, model and token usage.

## Analytics

| Method | Path | Permission |
| ------ | ---- | ---------- |
| GET | `/orgs/{org_id}/analytics/executions/` | `execution.view` |
| GET | `/orgs/{org_id}/analytics/executions/{id}/` | `execution.view` |
| GET | `/orgs/{org_id}/analytics/audit-logs/` | `audit.view` |
| GET | `/orgs/{org_id}/analytics/insights/` | `execution.view` |

`insights` returns real aggregates over recorded executions:
`{executions: {total, succeeded, failed, running, success_rate_percent}, top_tools[]}`.

## Health

`GET /_health/` (unauthenticated) — checks the database and Redis and returns 200 or
503. Used by container healthchecks and CI.

## Internal endpoints

`/internal/...` is **not** part of the public API. It requires a service token and an
organization scope header, and is documented separately in
[internal-ai-api.md](internal-ai-api.md).

## Money quote

> There are no fake endpoints. If a route is documented here, it is implemented and
> covered by tests. Anything not implemented is listed in
> [known-limitations.md](../development/known-limitations.md).
