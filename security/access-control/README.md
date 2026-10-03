# Access Control

The authoritative implementation is `apps/api/apps/common/rbac.py`. This document
explains it; the code is the source of truth. If they disagree, the code wins and
this page is a bug.

## Model

- **Organization** is the tenant boundary.
- **Membership** binds a user to an organization with exactly one **role**.
- Roles grant a fixed set of **permissions** (strings like `analyst.query`).
- The matrix lives in code, not in the database, so it is version-controlled,
  diffable and reviewable.

## Role → permission matrix

| Permission | viewer | analyst | admin | owner |
| ---------- | :----: | :-----: | :---: | :---: |
| `org.view` | ✔ | ✔ | ✔ | ✔ |
| `org.manage` | | | ✔ | ✔ |
| `member.manage` | | | ✔ | ✔ |
| `datasource.view` | ✔ | ✔ | ✔ | ✔ |
| `datasource.manage` | | | ✔ | ✔ |
| `document.view` | ✔ | ✔ | ✔ | ✔ |
| `document.manage` | | ✔ | ✔ | ✔ |
| `analyst.query` | | ✔ | ✔ | ✔ |
| `execution.view` | ✔ | ✔ | ✔ | ✔ |
| `audit.view` | | | ✔ | ✔ |

Owners currently hold the same permission set as admins; ownership is additionally
protected by the **last-owner invariant** (an organization can never lose its final
active owner — `organizations/services.py`, verified by
`test_cannot_remove_last_owner` / `test_cannot_demote_last_owner`).

## Non-negotiable rules

1. Authorization is decided **server-side**. The frontend's `lib/permissions.ts`
   only decides what to render.
2. A permission check is performed by a DRF permission class
   (`require_permission`) or `has_organization_permission`, never re-implemented
   inline in a view.
3. Non-members receive **404** for object routes, so resource existence is not
   disclosed.
4. Adding a permission requires: a matrix entry in `rbac.py`, a test in
   `apps/api/tests/security/test_authorization_matrix.py`, and an update to the
   table above.
5. Roles cannot be self-assigned; only `member.manage` holders change roles, and a
   user cannot change their own role through the members endpoint in the UI.

## Answering "can X do Y?"

```bash
cd apps/api
python -c "from apps.common.rbac import role_has_permission; print(role_has_permission('analyst','audit.view'))"
```

## Known limitation

There is no per-resource ACL beyond organization + role. For example, a viewer can
see every data source in the organization, not a subset. Row-level or
project-scoped access is explicitly out of scope for this release.
