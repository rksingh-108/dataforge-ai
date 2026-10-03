# Onboarding — Frontend Developer

## Your area

**You own:** `apps/web` (Next.js, React, TypeScript, Tailwind) and, jointly with
backend, `packages/shared-types`.

**You do not own:** business logic, authorization decisions, or anything that talks
to a database or an LLM. If you find yourself computing a rule in the browser,
stop — it belongs in `apps/api`.

## Set up

```bash
cd apps/web
npm install
API_BASE_URL=http://localhost:8000 npm run dev
```

You still need the API running (`docker compose up -d api db redis`, or the whole
stack). The browser never calls the API directly — everything goes through the BFF
at `/api/proxy/...`.

## Architecture rules you must follow

1. **Tokens stay server-side.** Never read or store a token in the browser. Use
   `/api/proxy/...` (via `clientFetch`) from client components and `apiFetch` from
   server components.
2. **Server Components by default.** Add `"use client"` only for interactivity,
   browser APIs, or hooks.
3. **Permissions gate rendering only.** `lib/permissions.ts` decides what to show.
   The API decides what is allowed. Never treat a hidden button as security.
4. **Three states for every async surface:** loading, empty, error. No exceptions.
5. **Accessibility is done-or-not-done:** labels on every input, keyboard
   reachable, visible focus, no colour-only status.

## Where things live

| Path | Purpose |
| ---- | ------- |
| `app/(app)/` | Authenticated pages sharing the app shell |
| `app/api/` | BFF route handlers (login, logout, proxy, org switch) |
| `app/login/` | Public sign-in |
| `components/` | Shared UI and feature components |
| `lib/api-server.ts` | Server-side API client |
| `lib/api-client.ts` | Browser client (through the proxy) |
| `lib/types.ts` | API response types |
| `lib/permissions.ts` | Permission constants and helpers |
| `lib/server-session.ts` | Resolves session + active organization |

## How to add a page

1. Create `app/(app)/<name>/page.tsx` as a Server Component.
2. Get the session with `loadSession()` — it redirects to `/login` when
   unauthenticated.
3. Fetch with `apiFetch` using an org-scoped path:
   `` `/api/v1/orgs/${organizationId}/...` ``.
4. Add an entry to `components/Sidebar.tsx` **with a permission** so it only shows
   to roles that can use it.
5. Move the interactive parts into a `"use client"` component.
6. Handle loading, empty and error states explicitly.

## Testing

```bash
npm run typecheck   # must be clean; strict mode is on
npm run test        # Vitest
npm run build       # production build must succeed
```

Unit-test logic (permission helpers, formatting, pure functions). Component tests
are welcome for interactive pieces. The build and typecheck are the hard gates.

## Definition of done (frontend)

- [ ] Typecheck, tests and production build pass
- [ ] Loading, empty and error states present
- [ ] Keyboard accessible; labels present; focus visible
- [ ] Responsive at mobile and desktop widths
- [ ] Permission-gated affordances added to the sidebar where relevant
- [ ] New API fields added to `lib/types.ts` and `packages/shared-types`
- [ ] No token, secret, or API host reachable from the browser

## Good first tasks

- Add an empty state where one is missing.
- Add a component test for an interactive component.
- Improve an error message so it tells the user what to do next.
- Make a table keyboard-navigable.

## Ask about

- Anything involving a new permission → backend + security owners.
- Anything that seems to need business logic in the browser → backend owner. It is
  almost certainly wrong.
