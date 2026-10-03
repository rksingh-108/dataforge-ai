# Incident Response

## Severity

| Level | Description | Response time | Examples |
| ----- | ----------- | ------------- | -------- |
| **SEV1** | Active cross-tenant exposure, credential compromise, or full outage | Immediate, all hands | Tenant data leak; Fernet key leak |
| **SEV2** | Significant degradation or a contained security event | 1 hour | Single-tenant data exposure; internal token leak |
| **SEV3** | Limited impact | Next business day | Elevated errors on one endpoint |
| **SEV4** | Low impact / hygiene | Backlog | Dependency CVE with no exploit path |

## Roles

| Role | Responsibility |
| ---- | -------------- |
| Incident Commander | Owns the response, makes the calls, keeps the timeline |
| Investigator | Reproduces and bounds the impact |
| Communicator | Status updates to stakeholders/customers |
| Scribe | Records the timeline in real time |
| Fixer | Implements the fix and rollback |

In a small team one person may hold several roles, but **the IC is never also the
Fixer** — someone must keep the overview.

## First 15 minutes

1. **Declare** the incident and its severity in the incident channel.
2. **Contain** before diagnosing:
   - Credential exposure → rotate the affected secret(s) immediately.
   - SSRF/outbound abuse → set `DATASOURCE_ALLOW_PRIVATE_NETWORKS=false`, or scale
     the AI service to zero to stop egress.
   - AI tool abuse → remove the offending tool from `build_default_registry()`.
   - Session compromise → rotate `DJANGO_SECRET_KEY` (invalidates all tokens).
3. **Preserve evidence**: capture `AuditLog` rows, `Execution` records, container
   logs and the current image tag **before** changing anything.
4. **Assess** scope: which organizations, which time window, which data.

## Investigation queries

```bash
# Credential access events (who retrieved a data-source password, and when)
docker compose exec api python manage.py shell -c "
from apps.analytics.models import AuditLog
qs = AuditLog.objects.filter(action__startswith='datasource.').order_by('-created_at')[:50]
for row in qs: print(row.created_at, row.action, row.actor_id, row.target_id, row.metadata)
"

# Login activity for a suspicious account
docker compose exec api python manage.py shell -c "
from apps.analytics.models import AuditLog
qs = AuditLog.objects.filter(action__startswith='auth.').order_by('-created_at')[:50]
for row in qs: print(row.created_at, row.action, row.actor_id, row.ip_address)
"
```

The audit log is append-only: if a row is missing, that is itself a finding.

## Communication

- SEV1/SEV2: update every 30 minutes until contained.
- Customer notification decisions involve legal and are not made by the engineer.
- Never speculate publicly about impact.

## After: postmortem (blameless)

Within 5 business days, write a postmortem covering:

1. **Impact** — what happened, to whom, for how long.
2. **Timeline** — detection, containment, resolution, with timestamps.
3. **Root cause** — the technical cause, not "human error".
4. **Detection** — did we notice? How long would it have taken if nobody had?
5. **Response** — what worked, what didn't.
6. **Action items** — each with an owner and a due date; add them to
   [`../vulnerability-management/README.md`](../vulnerability-management/README.md)
   when they concern a security gap.

## Recurring gaps to address

There is currently **no automated alerting** on security events. Detection today
depends on someone reading audit logs or a user reporting a problem. Alerting
rules are tracked as VM-10 in vulnerability management.
