# `infrastructure/deployment/`

Environment and deployment configuration owned by **DevOps**.

## Status

**No deployment target is configured.** The `deploy.yml` workflow builds and
publishes images but deploys nowhere until a target environment exists — known
limitation **P1**. See [`docs/deployment/README.md`](../../docs/deployment/README.md)
for the process, topology and the pre-flight checklist, and
[`scripts/deployment/`](../../scripts/deployment/) for the rollout helpers that
will live there.

## Why this directory is nearly empty

The rule for this repository is that a directory must have a real responsibility.
Writing Kubernetes manifests, Terraform, or a cloud-specific config for an
environment that has not been chosen would be invented work, not engineering. This
README records the decision and the constraints a future target must satisfy.

## Constraints any target must satisfy

| Constraint | Reason |
| ---------- | ------ |
| `ai-service`, `db`, `redis` have no public ingress | The AI service is an egress broker; the datastores hold platform data |
| TLS terminated at the edge | See [`../nginx/README.md`](../nginx/README.md) |
| Secrets injected from a secret manager | No secret in an image, a manifest or the repo (known limitation **S5**) |
| Migrations run separately, before rollout | A bad migration must be able to fail the release on its own |
| `/_health/` gates the rollout | A failing readiness check must abort, not serve traffic |
| Persistent `media` volume | Uploaded documents must survive a redeploy |
| One shared `INTERNAL_SERVICE_TOKEN` | `api` and `ai-service` must deploy together |

## Candidate shapes

1. **Single host + Compose** — closest to the local stack; simplest to operate.
2. **Managed container platform** — a container service plus a managed
   PostgreSQL with the `pgvector` extension and a managed Redis.
3. **Kubernetes** — deferred; known limitation **P3**. Only justified once there
   is a reason for autoscaling or multi-service scheduling.

Whichever is chosen, document it here and update P1, P3 and P4 accordingly.
