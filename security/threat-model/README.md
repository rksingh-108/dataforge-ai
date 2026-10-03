# Threat Model

## Method

We use a light **STRIDE** pass per trust boundary, driven by what the system
actually does rather than a generic checklist. Each model records:

- the assets in scope,
- the entry points and trust boundaries,
- concrete threats (with a short attack scenario),
- the control that addresses each threat, and where it lives in the code,
- **residual risk** — what is still possible after the control.

A threat model is a living document. If you change a boundary, change the model
in the same pull request. `CODEOWNERS` requires a security review for changes in
`security/`.

## Systems modelled

| Model | Surface | Trust boundary crossed |
| ----- | ------- | ---------------------- |
| [web-and-session.md](web-and-session.md) | Browser ⇄ Next.js BFF ⇄ API | Untrusted internet → authenticated session |
| [multi-tenancy.md](multi-tenancy.md) | API ⇄ platform database | Between organizations |
| [sql-injection.md](sql-injection.md) | AI service ⇄ customer databases | Model output → customer database |
| [ssrf.md](ssrf.md) | API/AI service → outbound network | User-supplied host → internal network |
| [prompt-injection.md](prompt-injection.md) | Documents/query results → model | Untrusted content → agent behaviour |
| [file-upload.md](file-upload.md) | Browser → API storage | User file → server filesystem/parsers |
| [secrets-and-credentials.md](secrets-and-credentials.md) | API ⇄ AI service ⇄ LLM vendors | Credential custody |

## Shared assumptions

1. **The API is the authority.** Any control placed only in the frontend or only
   in the AI service is assumed bypassable. The API re-checks every request.
2. **The model is untrusted output.** Anything the LLM produces — including SQL
   and tool arguments — is validated structurally before it can have an effect.
3. **Documents are untrusted input.** Uploaded content may be hostile.
4. **Compromise of the platform database is out of scope for these models**
   (encryption at rest, backups and DB hardening are infrastructure concerns
   documented in `security-architecture/`).
