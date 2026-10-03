# `packages/`

Versioned building blocks shared between applications. Each package has exactly
one responsibility; none contains runtime business logic.

| Package | Owner | Purpose |
| ------- | ----- | ------- |
| [`shared-types/`](shared-types/) | Frontend (+ backend) | TypeScript types mirroring API response shapes |
| [`api-contracts/`](api-contracts/) | AI (+ backend) | JSON Schemas for the API ⇄ AI-service boundary |
| [`config/`](config/) | DevOps | Shared, non-secret configuration values and conventions |

## Rules

1. **No secrets** in any package. Configuration packages carry defaults and
   conventions, never credentials.
2. **No runtime business logic.** If a package starts making decisions, it belongs
   in a service.
3. **Contract changes are breaking changes.** Update the package, the consuming
   code, and `CHANGELOG.md` in the same PR.
4. **No cross-service imports.** `apps/api` must not import TypeScript, and
   `apps/web` must not import Python. Packages are consumed by copying types or
   reading schemas — not by sharing a runtime.

## Why not a monorepo toolchain

There is no npm workspace or build step for `packages/`. The frontend consumes
`shared-types` through a TypeScript path alias, and `api-contracts` is read by both
sides as plain JSON. Adding a build pipeline for two small packages would be
tooling for its own sake; introduce one only when a package genuinely needs to be
published or compiled.
