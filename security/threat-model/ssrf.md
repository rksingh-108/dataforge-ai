# Threat model — Server-side request forgery (outbound connections)

## Scope

Any connection the platform opens to an address a user supplied. In this product
that is the **data-source connection path**: a user provides a host, port,
database, username and password, and the platform connects to it.

The AI service is the only component that opens those connections (see
`docs/architecture/service-boundaries.md`), which means it is the authoritative
egress point.

## Assets

- Internal network services (databases, admin panels, internal APIs).
- Cloud instance metadata endpoints (`169.254.169.254` and friends).
- The AI service's own loopback interface.

## Threats and controls

### T1 — Pointing a data source at a cloud metadata endpoint

*Scenario:* create a data source with host `169.254.169.254` and use the
connection-test result to read instance credentials.

*Controls:* link-local addresses are rejected. Both the API
(`apps/api/apps/datasources/validators.py`) and the AI service
(`ai_service/security/host_guard.py`) implement the same classification:
loopback, link-local (which includes `169.254.0.0/16`), multicast, reserved and
unspecified addresses are always rejected. The hostnames `metadata.google.internal`
and `metadata.goog` are rejected by name.

*Verified by:* `apps/api/apps/datasources/tests/test_datasources.py`
(`test_ssrf_validation_rejects_cloud_metadata`),
`apps/ai-service/tests/test_security.py` (`test_metadata_ip_is_rejected`,
`test_metadata_hostname_is_rejected`).

### T2 — Reaching internal RFC1918 services

*Scenario:* host `10.0.0.5` resolving to the internal admin API.

*Controls:* private ranges are rejected by default. They can only be enabled by
an operator setting `DATASOURCE_ALLOW_PRIVATE_NETWORKS=true`, which is a
deliberate, reviewable deployment decision (in practice this is paired with a
private network path such as a VPN or peering).

*Verified by:* `test_ssrf_validation_rejects_private_network`,
`test_private_ip_is_rejected_by_default`, `test_private_ip_is_allowed_when_opted_in`.

### T3 — Bypassing the check with a hostname or path traversal

*Scenario:* supply `evil.com/../metadata`, or a DNS name that resolves to a
blocked address.

*Controls:* hosts containing whitespace or slashes are rejected. Names are
**resolved and every returned address is checked**, so a name that resolves to one
permitted and one forbidden address is rejected outright. Only literal IPs skip
resolution.

*Verified by:* `test_hostname_resolving_to_private_ip_is_rejected`,
`test_host_with_slash_is_rejected`.

### T4 — TOCTOU / DNS rebinding

*Scenario:* the host resolves to a public address during validation and to
`169.254.169.254` when the driver connects moments later.

*Control:* validation is run **twice** — at data-source creation and again
immediately before opening the socket (the AI service's `_guard_host`). This
shrinks but does not eliminate the window.

**Residual risk (accepted, tracked):** a hostile or compromised DNS server can
still win the race. The complete fix is to connect to a pinned, pre-validated IP
address (or to route egress through a proxy that enforces the policy), which is
not implemented. This is listed in
[`../vulnerability-management/README.md`](../vulnerability-management/README.md).

### T5 — Redirect-based bypass

*Scenario:* the target returns an HTTP redirect to an internal address.

*Control:* not applicable — the platform opens raw TCP database connections, not
followed HTTP redirects. If an HTTP-based connector is added later, redirects
must be disabled or re-validated; this is a note for the future connector work.

### T6 — Using the AI service for unmetered egress

*Scenario:* an attacker with a valid service token uses "test connection" as a
generic port scanner.

*Controls:* the internal API requires the service token, which only the Django
API holds. Users cannot reach the AI service directly (no public route). Port
scanning is still possible *for hosts that pass the address checks*, and each
attempt is recorded in the audit log as `datasource.tested` /
`datasource.test_failed` with the actor, so it is detectable.

*Residual risk:* scanning of allowed (public) hosts is possible for an
authenticated user with `datasource.manage`. Rate limiting on this endpoint is
not implemented.

## Operational guidance

- Keep `DATASOURCE_ALLOW_PRIVATE_NETWORKS=false` unless a private path and a
  compensating control are in place.
- Alert on repeated `datasource.test_failed` audit events for the same actor.
- Treat the AI service as an egress broker: give it no credentials beyond the
  internal service token and no inbound public exposure.
