# `database/migrations/`

SQL that must run **outside** Django migrations, such as:

- enabling a database extension before Django touches the schema,
- helper functions or types shared by several Django migrations,
- one-off corrective SQL for a specific incident (kept for the record).

Django migrations are **not** kept here. They live next to their app:

```
apps/api/apps/<app>/migrations/
```

## Why the split

Django needs migrations inside the app package it is managing, and it orders them
by its own dependency graph. Trying to keep them in a central directory fights the
framework for no benefit. What does not belong to a Django app — extension setup,
raw SQL, corrective scripts — lives here instead.

## Adding a file here

1. Name it `<sequence>_<description>.sql`, e.g. `0001_pgvector_extension.sql`.
2. Make it **idempotent** (`IF NOT EXISTS`, `CREATE OR REPLACE`).
3. Document, at the top of the file, *when* it must run and *who* applies it.
4. If an application migration depends on it, link to this file from that
   migration's docstring.

## Current contents

Empty. The pgvector extension is enabled by
`apps/api/apps/documents/migrations/0000_enable_pgvector.py`, which keeps the
dependency visible to Django so the ordering is guaranteed. Copy that pattern
rather than adding a raw SQL file here when you can.
