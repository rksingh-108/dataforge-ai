# Contributing to DataForge AI

This document is the contract for how work gets proposed, built, reviewed and
merged. Read it once; it will not change without a PR you can review.

## Ground rules

1. **No work without an issue.** If it is not worth an issue, it is not worth a PR.
2. **Small PRs.** Aim under ~400 changed lines. A reviewer who cannot hold the
   change in their head will miss something.
3. **Tests and docs ship with the change**, not after it.
4. **Never commit secrets, credentials or real customer data.**
5. **Do not weaken a check to make CI pass.** Fix the cause, or say why the check
   itself is wrong — in the PR, for others to agree with.

## Ownership

| Area | Owner | Paths |
| ---- | ----- | ----- |
| Web / UI | Frontend | `apps/web`, `packages/shared-types` |
| API / domain | Backend | `apps/api` |
| AI / LLM / RAG | AI | `apps/ai-service`, `packages/api-contracts` |
| Schema / migrations / seeds | Data | `database`, `apps/api/apps/*/migrations` |
| Infra / CI-CD | DevOps | `infrastructure`, `.github`, `scripts/deployment` |
| Security | Security | `security`, `tests/security`, `apps/api/apps/common` |
| Test strategy | QA | `tests`, `scripts/testing` |
| Documentation | Docs | `docs`, `README.md`, `CONTRIBUTING.md` |

[`.github/CODEOWNERS`](.github/CODEOWNERS) turns this into enforced review. If you
are unsure whether your change crosses an area, ask before opening the PR.

## The workflow

```
Issue → assignment → feature branch → implementation → tests
      → lint/type checks → pull request → CI → review → approval → merge
```

### 1. Issue

Use the templates in `.github/ISSUE_TEMPLATE/`. A good issue states the problem,
the acceptance criteria, and any security considerations. Never describe an
exploitable vulnerability in a public issue — see [SECURITY.md](SECURITY.md).

### 2. Branch

```bash
git switch main && git pull
git switch -c <type>/<short-description>
```

| Type | Use for |
| ---- | ------- |
| `feat/` | New capability |
| `fix/` | Bug fix |
| `refactor/` | Behaviour-preserving restructure |
| `docs/` | Documentation only |
| `test/` | Tests only |
| `chore/` | Tooling, dependencies, config |
| `security/` | Security fix or hardening |

Use kebab-case and keep it short: `feat/datasource-notes`, `fix/empty-state-copy`.

### 3. Implementation

Follow [docs/development/coding-standards.md](docs/development/coding-standards.md)
and [docs/development/adding-a-feature.md](docs/development/adding-a-feature.md).

### 4. Tests

Every behaviour change needs a test that fails without it. Security fixes need a
test named after the attack. See
[security/security-testing/README.md](security/security-testing/README.md).

### 5. Local checks

```bash
make ci          # boundary checks + all tests + lint
make security    # bandit, pip-audit, secret scan, Django --deploy
```

Run these before pushing. They are the same checks CI runs, so a local pass
predicts a green pipeline.

### 6. Commit messages

Conventional commits, imperative mood, scoped:

```
type(scope): imperative summary

Why this change is needed, if not obvious from the summary.

Refs #123
```

Examples:

```
feat(datasources): add notes field to data sources
fix(web): show an empty state when no executions exist
security(sql): reject data-modifying CTEs
docs(onboarding): clarify how to run the AI service tests
```

Allowed types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `security`,
`perf`. Allowed scopes match the ownership table plus `ci`, `db`, `deps`.

### 7. Pull request

Open it as a **draft** early if you want feedback before it is finished. Fill in
the [template](.github/PULL_REQUEST_TEMPLATE.md) honestly — especially the
Definition of Done and the security review section.

Include:

- what changed and **why**,
- how you verified it (exact commands and results),
- any deliberate limitation, with a link to
  [docs/development/known-limitations.md](docs/development/known-limitations.md).

### 8. CI

CI runs on every PR. Common failures:

| Failure | Fix |
| ------- | --- |
| `Service boundaries` | You imported across a boundary; see `docs/architecture/service-boundaries.md` |
| Backend tests | Run `make test-backend` locally; the suite needs Postgres+pgvector and provides it |
| `ruff` | `make format` |
| `check --deploy` | The change made a production setting unsafe |
| Frontend build | `cd apps/web && npm run build` locally |
| Coverage below 70% | Add tests for the code you added |

### 9. Review

Reviewers check correctness, then security, then tests, then readability, then docs.

| Requirement | Rule |
| ----------- | ---- |
| Approvals | One minimum; two for security-critical areas |
| Security areas | A security owner must approve |
| Author's own PR | The author never approves their own PR |
| Response time | Reviewers respond within one business day |
| Re-review | After changes, request it again — a stale approval is not approval |

**As a reviewer:** approve when it is good enough and safe, not when it is how you
would have written it. Ask questions rather than issuing commands. Block only for
correctness, security or maintainability — not style a formatter could fix.

**As an author:** a review comment is about the code. If you disagree, explain why.
Do not silently change the subject.

### 10. Merge

- Squash merge into `main`, with the PR title as the commit subject.
- Delete the branch.
- Verify `main` is green after merge. If it is not, the author or the reviewer
  fixes it immediately — a red `main` blocks everyone.

## Definition of Done

A change is done when **all** of the following are true:

1. Acceptance criteria from the issue are met.
2. Tests exist, are meaningful, and fail without the change.
3. `make ci` passes locally and in the pipeline.
4. Documentation is updated in the same PR.
5. API changes are reflected in `packages/api-contracts/`.
6. No secrets, no real customer data, no new suppressions without justification.
7. Tenant isolation is preserved: every new query and endpoint is org-scoped.
8. Authorization is declared explicitly on every new endpoint.
9. Required approvals are in place and CI is green.
10. Any deliberate limitation is documented in
    [docs/development/known-limitations.md](docs/development/known-limitations.md).

## Documentation requirements

Update documentation in the same PR when you change behaviour. Where:

| Change | Document |
| ------ | -------- |
| New endpoint or field | `docs/api/`, `packages/api-contracts/` |
| New permission | `security/access-control/README.md` + the matrix test |
| Schema change | `database/README.md`, `docs/database/schema.md` |
| New AI tool | `docs/ai/tools.md` |
| New config variable | `.env.example` + `docs/deployment/README.md` |
| New control or gap | `security/README.md` or vulnerability management |
| Anything partial | `docs/development/known-limitations.md` |

## Getting help

| Question | Where |
| -------- | ----- |
| How do I run this? | [docs/development/local-setup.md](docs/development/local-setup.md), [debugging.md](docs/development/debugging.md) |
| Where does this belong? | [docs/architecture/service-boundaries.md](docs/architecture/service-boundaries.md) |
| Is this secure? | The security owner listed in `CODEOWNERS` |
| I am new | [docs/onboarding/new-developer.md](docs/onboarding/new-developer.md) |

## Code of conduct

Be direct about the work and generous about the person. Assume competence and good
intent. Criticism is welcome; contempt is not.
