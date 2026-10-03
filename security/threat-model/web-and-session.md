# Threat model — Web app and session handling

## Trust boundary

Untrusted internet → Next.js server (BFF) → Django API. The browser is assumed
hostile: it may run injected scripts, and any value it sends may be tampered with.

## Session design

- Login is handled by the Next.js BFF (`/api/auth/login`). Django returns an
  access token (15 min) and a rotating refresh token (7 days).
- Both are stored in **httpOnly, SameSite=Lax** cookies (`secure` in production).
  JavaScript cannot read them, so XSS cannot steal a session token.
- All API calls from the browser go to same-origin `/api/proxy/...`, which
  attaches the token server-side and refreshes once on a 401.
- Refresh tokens are rotated and blacklisted after use
  (`ROTATE_REFRESH_TOKENS`, `BLACKLIST_AFTER_ROTATION`).
- Changing a password blacklists every outstanding refresh token for the user.

## Threats and controls

| # | Threat | Control | Verified by |
| - | ------ | ------- | ----------- |
| T1 | Token theft via XSS | httpOnly cookies; no token in JS-accessible storage | `apps/web/lib/session.ts` (review); proxy keeps tokens server-side |
| T2 | CSRF from another origin | `SameSite=Lax` cookies; state-changing routes only accept same-origin `POST`/`PATCH`/`DELETE`; Django `CSRF_TRUSTED_ORIGINS` is explicit | Configuration in `config/settings/*` |
| T3 | Session fixation | New tokens are issued on every login; no server-side session id is reused | `LoginView` |
| T4 | Brute-force login | Scoped DRF throttle `auth` (10/min) | `test_*` in `apps/api/tests/security/test_rate_limiting.py` |
| T5 | Refresh-token replay | Rotation + blacklist; reuse fails with 401 | `test_logout_blacklists_refresh_token`, `test_refresh_rotates_token` |
| T6 | Clickjacking | `X-Frame-Options: DENY` at Next.js and Django | `apps/web/next.config.ts`, `config/settings/base.py` |
| T7 | MIME sniffing | `X-Content-Type-Options: nosniff` on both tiers | as above |
| T8 | Mixed content / insecure cookie | `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, HSTS in production | `config/settings/production.py` |
| T9 | Privilege escalation via UI | UI gating is cosmetic; API enforces every permission | `test_analyst_cannot_add_member`, `test_viewer_cannot_create_datasource` |
| T10 | Open redirect | No redirect endpoint; the proxy uses `redirect: "manual"` | `apps/web/app/api/proxy/[...path]/route.ts` |

## Residual risk

- **CSP is not implemented.** A Content-Security-Policy header would add defence in
  depth against XSS. Tracked in [`../vulnerability-management/README.md`](../vulnerability-management/README.md).
- **No edge rate limiting.** Throttles are per-application-process; behind
  multiple workers the effective limit is per-worker. An edge/WAF limiter is a
  deployment concern.
- **Session revocation granularity.** Individual sessions cannot be listed or
  revoked one at a time; "sign out everywhere" is the available action.
