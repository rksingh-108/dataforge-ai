# Coding Standards

These are enforced where possible and expected everywhere. When tooling and taste
disagree, the tool wins.

## Universal

- **Small files, one responsibility.** If a module needs a table of contents, split it.
- **Name for the domain, not the technology.** `DatasourceConnectionError`, not `NetworkException`.
- **Comments explain *why*.** The code already says *what*.
- **No dead code, no commented-out code.** Git remembers.
- **No "temporary" hacks without an issue reference** in the comment.
- **Errors are values, not silence.** Never `except Exception: pass`. If you truly
  must swallow (best-effort broadcasting, closing a connection), say why in a
  comment.

## Python

- Target 3.13+. Use type hints on public functions and dataclasses where they add clarity.
- `from __future__ import annotations` at the top of every module using annotations.
- Ruff for lint and format. Configuration at the repo root; CI runs `ruff check`.
- **Layering, enforced by review:**
  - Views: authorization + delegation only. No ORM writes, no business rules.
  - Serializers: shape and field-level validation only.
  - Services: writes and invariants, inside transactions where multiple rows change.
  - Selectors: reads, always tenant-scoped.
- Raise **domain exceptions** (`apps.common.exceptions`), not bare `Exception`.
- `AuditLog` is append-only; never add an update path.
- Never log a credential. `RedactingFormatter` is a safety net, not a licence.

### Django specifics

- Models inherit `BaseModel`/`OrganizationScopedModel`.
- Every model has explicit `Meta.ordering` and indexes for the queries you write.
- Migrations are generated, reviewed, and committed with the model change.
- Never call `.save()` inside a serializer.

## TypeScript / React

- `strict` and `noUncheckedIndexedAccess` are on. Do not weaken them.
- No `any`. Use `unknown` and narrow.
- Server Components by default; `"use client"` only where interactivity or browser
  APIs are needed.
- Data fetching in Server Components uses `apiFetch`; client components use
  `clientFetch` (through the BFF). Never fetch the API host from the browser.
- UI permission checks use `lib/permissions.ts` **for rendering only**. Never treat
  them as security.
- Accessibility is part of the definition of done: labels on inputs, `aria-*`
  where needed, keyboard reachable, visible focus, no colour-only signals.
- Every list has an empty state; every async action has a loading state; every
  failure path has an error state.

## SQL

- Application SQL is parameterised. String interpolation into SQL is prohibited.
- AI-generated SQL never executes as written: parse, validate, then execute
  read-only (see `security/threat-model/sql-injection.md`).

## Tests

- Name tests after behaviour, not implementation: `test_cannot_demote_last_owner`.
- One logical assertion per test where practical; use `pytest.mark.parametrize` for
  matrices.
- Security tests name the attack (see
  `security/security-testing/README.md`).
- A bug fix ships with the failing test that proves it.

## Commits and branches

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for the full workflow. Short version:
`type(scope): imperative summary` and a branch named
`<type>/<short-description>`.

## Reviews

Reviewers check, in order:

1. Correctness and edge cases.
2. Security: tenancy, authorization, secrets, outbound calls, SQL.
3. Tests: do they fail without the change?
4. Readability and naming.
5. Documentation updated in the same PR.

Style preferences that a formatter could fix are not review comments.
