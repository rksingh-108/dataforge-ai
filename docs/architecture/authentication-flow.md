# Authentication Flow

## Overview

DataForge AI uses **JWT** access tokens with a **rotating refresh token**, held in
**httpOnly cookies** by a Next.js BFF. This keeps tokens out of reach of
JavaScript while allowing a stateless API.

```
┌─────────┐   credentials    ┌──────────────┐   credentials    ┌────────────┐
│ Browser │ ───────────────▶ │ Next.js BFF  │ ───────────────▶ │ Django API │
│         │                  │ (route       │                  │            │
│         │ ◀─────────────── │  handler)    │ ◀─────────────── │            │
└─────────┘   profile +      └──────────────┘   access+refresh └────────────┘
              httpOnly cookies
```

## Why the BFF pattern

A pure SPA must store tokens somewhere the browser can read them (memory or
`localStorage`). Memory is lost on refresh; `localStorage` is readable by any XSS.
The BFF keeps the token server-side and the browser receives only a
same-origin session cookie the script cannot read.

Trade-off: the Next.js server is now part of the trust boundary and must be
deployed with the same care as the API. This is recorded in
[`security/threat-model/web-and-session.md`](../../security/threat-model/web-and-session.md).

## Token strategy

| Token | Lifetime | Storage | Rotation |
| ----- | -------- | ------- | -------- |
| Access | 15 minutes (`JWT_ACCESS_TTL_MINUTES`) | httpOnly cookie | Issued on login and refresh |
| Refresh | 7 days (`JWT_REFRESH_TTL_DAYS`) | httpOnly cookie | Rotated on every refresh; old token blacklisted |

- `ROTATE_REFRESH_TOKENS = True` and `BLACKLIST_AFTER_ROTATION = True`
  (`config/settings/base.py`).
- Blacklisting uses `rest_framework_simplejwt.token_blacklist`.
- A **reused** refresh token fails with 401 — replay is rejected.
- Changing a password blacklists every outstanding refresh token for that user
  (`PasswordChangeView._revoke_all_refresh_tokens`), which signs out all sessions.

## Endpoints

| Method | Path | Auth | Purpose |
| ------ | ---- | ---- | ------- |
| POST | `/api/v1/auth/login/` | none (throttled `auth`) | Authenticate, return tokens + memberships |
| POST | `/api/v1/auth/refresh/` | refresh token | Rotate to a new access token |
| POST | `/api/v1/auth/logout/` | access token | Blacklist the refresh token |
| POST | `/api/v1/auth/password/change/` | access token | Change password, revoke all sessions |
| GET | `/api/v1/me/` | access token | Current user, memberships and permissions |

## Login sequence (detailed)

1. Browser posts `{email, password}` to the BFF (`/api/auth/login`).
2. BFF posts to `/api/v1/auth/login/`, sends no cookies, `cache: "no-store"`.
3. API: throttled by scope `auth`; `authenticate()` then `is_active` check.
   - Failure → 401 with a generic message; `auth.login_failed` is recorded with
     the email **domain only** (never the full address or the password).
   - Success → `RefreshToken.for_user(user)`; `auth.login` recorded.
4. BFF stores `access` and `refresh` as httpOnly cookies and sets `df_org` to the
   first membership.
5. Browser is redirected to `/dashboard`; the server component calls `/api/v1/me/`
   with the cookie.

## Refresh during a request

`/api/proxy/[...path]` forwards the request with the access token. On a **401**:

1. It exchanges the refresh cookie at `/api/v1/auth/refresh/`.
2. On success, it stores the new access token (the API also rotates the refresh
   token; the BFF stores the new one) and retries the original request **once**.
3. On failure it clears all session cookies and returns 401, and the UI redirects
   to `/login`.

A single retry prevents infinite loops against a broken refresh endpoint.

## WebSocket authentication

Browsers cannot set an `Authorization` header on a WebSocket handshake, so the
access token is passed as `?token=...` at connect time only and is never stored
server-side beyond the connection. `JWTAuthMiddleware` validates it and resolves
the user; **anonymous sockets are closed immediately** (code 4401). The consumer
then re-checks organization membership before joining a group (code 4403 on
failure) — the token is not trusted for authorization.

## Password policy

Django validators, enforced at the API layer:

- minimum length 10,
- not too similar to the user's attributes,
- not a common password,
- not entirely numeric.

Additionally, the new password must differ from the current one
(`PasswordChangeSerializer.validate`).

## Failure modes

| Situation | Behaviour |
| --------- | --------- |
| Wrong password | 401 `invalid_credentials`, audited |
| Inactive user | 401, no token issued |
| Expired access token | BFF refreshes once, then 401 → `/login` |
| Expired/blacklisted refresh token | 401, cookies cleared |
| Tampered cookie | Signature check fails → 401 |
| No membership in any organization | Redirect to `/no-organization` |

## Not implemented (honest)

- Multi-factor authentication.
- Email verification / password reset by email (no mail provider is wired up).
- SSO / OIDC.
- Per-session revocation UI ("sign out everywhere" exists via password change).
