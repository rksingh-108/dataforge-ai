# `scripts/`

Automation shared by developers and CI. The rule is simple: **if CI runs it, it
lives here**, so a local run and a pipeline run are the same code.

| Directory | Owner | Purpose |
| --------- | ----- | ------- |
| [`dev/`](dev/) | Platform | Local quality and boundary checks |
| [`database/`](database/) | Data | Migration, seed and database maintenance helpers |
| [`testing/`](testing/) | QA | Test runners (each provisions what it needs) |
| [`deployment/`](deployment/) | DevOps | Release and rollout helpers |

## Conventions

1. **Bash for orchestration, Python for logic.** A shell script that needs more
   than a few conditionals should be a Python script.
2. `set -euo pipefail` at the top of every bash script.
3. **Self-provision.** A test runner starts what it needs (for example
   `testing/run-backend-tests.sh` starts a throwaway Postgres+pgvector container)
   and cleans up with a `trap`, even on failure.
4. **Print what you do** so a failure is diagnosable from CI logs alone.
5. **Exit non-zero on failure.** CI depends on the exit status, not on the text.
6. **No secrets in scripts.** Read them from the environment; never hard-code them.
7. Keep them small and single-purpose. When a script grows past ~100 lines, it
   should probably be its own tool with tests.

## Making a script executable

```bash
chmod +x scripts/<dir>/<script>.sh
```

Git tracks the executable bit; a script that is not executable will fail in CI.

## Entry points

Most developers should use the Makefile rather than calling scripts directly.
`make help` lists the targets, and each one maps to a script here.
