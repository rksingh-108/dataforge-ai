# Reverse proxy (TLS termination)

**Status: documented contract, no configuration shipped.** This directory exists
because the production topology requires a reverse proxy in front of `web` and
`api`, and that contract needs an owner and a place to live. It is tracked as
known limitation **P2** in
[`docs/development/known-limitations.md`](../../docs/development/known-limitations.md).

The local Compose stack does **not** use a proxy: it publishes each service port
directly for developer convenience. **Do not copy that posture to production.**

## What the proxy must do

| Requirement | Detail |
| ----------- | ------ |
| Terminate TLS | TLS 1.2+ only; redirect HTTP → HTTPS; HSTS with a long max-age |
| Route `web` | `/` → `web:3000` |
| Route `api` | `/api/` and `/_health/` → `api:8000` |
| Route WebSocket | `/ws/` → `api:8000` with `Upgrade`/`Connection` headers forwarded |
| Never expose `ai-service` | No route. It is an egress broker reachable only by `api` |
| Never expose `db` / `redis` | Private network only |
| Preserve correlation | Forward `X-Request-Id`; generate one if the client omits it |
| Bound request size | Reject bodies above `DOCUMENT_MAX_UPLOAD_BYTES` (25 MB default) before they reach the API |
| Timeouts | Read timeout comfortably above `INTERNAL_REQUEST_TIMEOUT_SECONDS` so analyst runs are not cut off |
| Security headers | The API sets `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`; the edge may add CSP (see known limitation **S3**) |

## Why a proxy and not application TLS

Certificates and renewal are an environment concern, not an application one. Keeping
termination at the edge means the services stay plain HTTP on a private network and
no certificate ever enters a container image or this repository.

## What must be added before this is production-ready

1. A concrete configuration file (nginx or an equivalent ingress) implementing the
   table above.
2. Certificate provisioning and renewal, with the private key **outside** the repo.
3. A test that the WebSocket upgrade path works through the proxy — the API's
   Channels consumer is real (see `apps/api/apps/realtime/`) but has not been
   exercised behind a proxy.
4. A CI or deployment check that a bad certificate or a missing route fails the
   rollout rather than serving 502s.

When the configuration is added, replace this README's status line and update P2.
