# Database Documentation

The authoritative schema reference is
[`docs/database/schema.md`](../../docs/database/schema.md).

This directory is for database-specific notes that do not belong in the general
docs tree:

- query performance findings and the indexes they motivated,
- notes on pgvector tuning (HNSW parameters, index build time at scale),
- backup/restore procedures validated against a real restore,
- anything about the *storage engine* rather than the *domain*.

## Adding a note

Prefer a short, dated markdown file over a long-lived document, for example
`2026-10-03-hnsw-tuning.md`, describing:

1. What was measured, and on what data volume.
2. The change made (index or query).
3. The observed effect.

Do not record performance numbers you have not measured. This repository makes no
performance claims anywhere (see known limitation P5).
