# `database/fixtures/`

Fixture data for local development and tests.

## Current state

This directory is intentionally **empty**. Tests build their objects through the
ORM via fixtures in `apps/api/conftest.py`, which exercises the same code paths
production uses and keeps the data explicit next to the assertions.

A static fixture file would be a second source of truth for the same objects, and
would need updating every time a model changes. Neither is desirable.

## When to add a fixture here

Add one only when all of the following hold:

1. The data is large or awkward to build in code (for example, a synthetic corpus
   of documents for retrieval tuning).
2. It must be byte-identical between runs.
3. It contains no real data and no secrets.

Then:

- name it `<purpose>.json` or `<purpose>.jsonl`,
- document at the top what it contains and which tests use it,
- add a loader to `scripts/database/`.

## Rules

1. **Synthetic data only.** Never real customer data, in any form, including
   "anonymised" extracts.
2. **No credentials or tokens.**
3. Keep it small. A fixture larger than a few hundred kilobytes should live in
   object storage, not in git.
