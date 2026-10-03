# `@dataforge/shared-types`

TypeScript mirrors of the API's response shapes, plus the permission constants.

## What this package is

A single file of **type declarations** and one `const` object of permission
strings. No runtime logic, no classes, no validation.

It exists so that:

- the frontend has one place to look up a wire shape,
- a serializer change is a compile error in the frontend rather than a runtime bug,
- permission strings are not retyped (and mistyped) across components.

## What this package is not

- **Not a domain model.** If a type needs behaviour, the behaviour belongs in
  `apps/api`.
- **Not validation.** The API validates; the client trusts the shape (and renders
  an error if it is wrong).
- **Not shared with Python.** `apps/api` has its own serializers. Keeping one
  source of truth across two languages would require code generation, which is not
  justified at this size; the JSON Schemas in `packages/api-contracts/` cover the
  boundary that actually needs a machine-readable contract.

## Usage

The frontend imports it through a path alias (`@/lib/types` re-exports for
convenience). There is no build step: the package ships `.ts` source and is
consumed by the Next.js compiler.

## Keeping it accurate

Update this file in the **same PR** as the serializer change. A stale type is worse
than no type, because it makes the frontend confidently wrong.

Checklist when a serializer changes:

- [ ] `packages/shared-types/src/index.ts`
- [ ] `apps/web/lib/types.ts` (if the shape is used directly by pages)
- [ ] `packages/api-contracts/` (if the change crosses the API ⇄ AI boundary)
- [ ] `docs/api/README.md`
- [ ] `CHANGELOG.md`
