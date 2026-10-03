# Threat model — Document upload and parsing

## Trust boundary

Browser → API (storage) → Celery worker → AI service (parsers: pypdf, python-docx).

Uploaded files are attacker-controlled and are parsed by third-party libraries.
Two risks follow: hostile content reaching a parser, and hostile content reaching
the model (see [prompt-injection.md](prompt-injection.md)).

## Threats and controls

| # | Threat | Control | Where |
| - | ------ | ------- | ----- |
| T1 | Executable uploaded as a "PDF" | Magic-byte check: `%PDF` for PDF, ZIP signature for DOCX; extension must match the declared content type | `apps/api/apps/documents/validators.py` |
| T2 | Path traversal via filename | Filenames are never used as paths; storage uses `documents/<org>/<uuid>.<ext>` | `documents/models.py` (`document_upload_path`) |
| T3 | Zip-bomb / oversized file | `DOCUMENT_MAX_UPLOAD_BYTES` (default 25 MB) enforced before reading | `validators.py`, `settings/base.py` |
| T4 | Unicode / null-byte tricks in TXT | TXT must decode as UTF-8 and must not contain null bytes | `validators.py` |
| T5 | Duplicate flooding | SHA-256 checksum with a per-organization unique constraint returns 409 | `documents/models.py`, `services.create_document` |
| T6 | Denial of service via a pathological document | Parsing runs asynchronously in Celery with a time limit, so a slow file cannot block HTTP | `documents/tasks.py`, `CELERY_TASK_TIME_LIMIT` |
| T7 | Malware distributed through the knowledge base | **Not implemented.** Files are validated, not scanned. | Gap — see below |
| T8 | Stored XSS via document text rendered in the UI | Document content is rendered as text (`whitespace-pre-wrap`), never as HTML | `apps/web/components/AnalystConsole.tsx` |

## Verified by

`apps/api/apps/documents/tests/test_documents.py`:
`test_upload_rejects_disallowed_extension`,
`test_upload_rejects_magic_byte_mismatch`,
`test_upload_rejects_duplicate_content`,
`test_processing_failure_marks_document_failed`.

## Residual risk (accepted, tracked)

- **No antivirus / content disarm.** A malicious file that survives our type
  checks will be parsed by pypdf/python-docx inside the worker container. The
  containers run as non-root with no privileged mounts, which limits blast radius
  but does not eliminate parser CVEs. Adding ClamAV (or a managed scanning
  service) at upload time is the recommended next step and is tracked in
  [`../vulnerability-management/README.md`](../vulnerability-management/README.md).
- **Documents are not encrypted at rest** beyond the storage layer's own
  encryption. Object-storage encryption is a deployment control.
- Parser dependencies (`pypdf`, `python-docx`) are third-party and are covered by
  `pip-audit` in CI, which detects known CVEs but not unknown ones.
