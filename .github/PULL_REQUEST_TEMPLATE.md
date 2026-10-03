<!--
Thanks for contributing to DataForge AI. Keep this description short and useful:
reviewers care about *why*, *what changed*, and *how you verified it*.
-->

## What and why

<!-- One or two sentences. Link the issue: "Closes #123". -->

## Area of change

- [ ] Web (`apps/web`)
- [ ] API / domain (`apps/api`)
- [ ] AI service (`apps/ai-service`)
- [ ] Database / migrations (`database`, app migrations)
- [ ] Infrastructure / CI (`infrastructure`, `.github`, scripts)
- [ ] Security (`security`, security tests)
- [ ] Documentation only

## How this was verified

<!--
Be specific. "Ran the tests" is not enough. Include the exact commands and the
result, and describe any manual verification.
-->

```
# e.g.
make test-backend      # 57 passed
make test-ai           # 94 passed
make test-web          # 15 passed
make check-boundaries  # Service boundaries OK.
```

## Definition of Done

<!-- See CONTRIBUTING.md for the full text. -->

- [ ] Tests added or updated for the new behaviour (and they fail without my change)
- [ ] Documentation updated (docs/, security/, README, CHANGELOG)
- [ ] API changes are reflected in `packages/api-contracts/`
- [ ] No secrets, credentials, or real customer data in the diff
- [ ] No new `# noqa`, `type: ignore`, or skipped test without an explanation below
- [ ] Tenant isolation considered: every new query/endpoint is scoped to an organization
- [ ] Authorization considered: the new endpoint declares its required permission

## Security review

<!-- Tick if applicable; a security owner must review when any box is ticked. -->

- [ ] Touches authentication, authorization or session handling
- [ ] Touches tenant isolation or raw SQL
- [ ] Touches credential storage or encryption
- [ ] Introduces a new outbound network call (SSRF surface)
- [ ] Adds or changes a file upload path
- [ ] Not applicable

## Database changes

- [ ] No migration
- [ ] Migration included and reversible
- [ ] Data migration with a rollback plan described below

## Reviewer notes

<!-- Anything you want reviewers to look at first, or known follow-up work. -->
