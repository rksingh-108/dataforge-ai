# Onboarding — New Developer

Welcome. This guide gets you from zero to a merged pull request. Budget **one
day** for setup and orientation, then pick up your first issue.

## Hour 1 — Understand what we are building

1. Read [README.md](../../README.md) (10 min).
2. Read [system-overview.md](../architecture/system-overview.md) (15 min).
3. Read [service-boundaries.md](../architecture/service-boundaries.md) (10 min).
4. Skim [known-limitations.md](../development/known-limitations.md) so you know what
   is real and what is not (10 min).

You should be able to answer: *what are the three applications, and which one owns
the platform database?*

## Hour 2 — Run it

Follow [local-setup.md](../development/local-setup.md). Docker is the fast path.

```bash
cp .env.example .env        # generate the three secrets listed in the file
docker compose up --build
docker compose exec api python manage.py seed_development
```

Then sign in at <http://localhost:3000/login> as `owner@dataforge.local` /
`DataForge!Dev1`.

Success looks like: dashboard loads, you can open Data Sources, Documents and
Executions.

## Hour 3 — Run the tests

```bash
make test            # backend + AI service + frontend
```

Everything must pass before you change anything. If it does not, that is your
first problem to report (with the failing output).

## Hour 4 — Read the rules

1. [coding-standards.md](../development/coding-standards.md)
2. [adding-a-feature.md](../development/adding-a-feature.md)
3. [CONTRIBUTING.md](../../CONTRIBUTING.md)
4. [security/policies/README.md](../../security/policies/README.md) — short, and
   the fastest way to avoid a rejected PR

## Day 2 — Your first change

Pick a `good first issue`. Good candidates are small, local and testable:

- improve an empty state or error message in `apps/web`,
- add a missing test that reproduces a bug,
- fix a documentation inaccuracy.

Then:

```bash
git switch -c fix/<what-you-are-fixing>
# ... make the change, add a test ...
make ci
git commit -m "fix(web): correct the empty state on the documents page"
git push -u origin HEAD
```

Open a **draft PR** early and ask your mentor to look. Do not wait until it is
perfect — a draft with a question is faster than a perfect PR with a wrong
assumption.

## How we work

| Practice | Expectation |
| -------- | ----------- |
| Branch naming | `<type>/<short-description>` — see CONTRIBUTING.md |
| Commits | `type(scope): imperative summary` |
| PR size | Prefer under ~400 changed lines. Split large work. |
| Reviews | One approval minimum; CODEOWNERS decides for sensitive areas |
| Tests | Every behaviour change has a test |
| Docs | Updated in the same PR, not later |
| Blockers | Say so within half a day; do not sit on a problem |

## Where to ask

| Question | Ask |
| -------- | --- |
| "How do I run this?" | [debugging.md](../development/debugging.md), then your mentor |
| "Is this secure?" | Security owner (see [CODEOWNERS](../../.github/CODEOWNERS)) |
| "Where does this belong?" | [service-boundaries.md](../architecture/service-boundaries.md) |
| "Is this in scope?" | The issue. If unclear, ask before building. |

## Intern guidance

- Your first issue will be deliberately small. Finishing it end-to-end (including
  tests and docs) matters more than the size.
- Ask questions early. A question at hour one is cheaper than a rewrite at day two.
- You are never expected to touch tenancy, authorization, cryptography or SQL
  safety without a mentor pair-reviewing. Those areas have tests precisely because
  mistakes there are expensive.
- If you find something broken, say so. Being the person who found a real bug is a
  contribution, not an embarrassment.

## Traps to avoid

1. **Adding a folder or abstraction to look thorough.** Every directory must have a
   real responsibility.
2. **Mocking the thing you are testing.** Tests must exercise the real component;
   only true external boundaries are stubbed.
3. **Hiding a button and calling it authorization.** The API enforces access.
4. **Describing something as done when it is partial.** Add it to
   [known-limitations.md](../development/known-limitations.md) instead.
5. **Big PRs.** They are hard to review and hide problems.
