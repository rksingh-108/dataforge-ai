# LinkedIn profile copy — DataForge AI

Ready-to-paste text for the **About** section, the **Featured** card, and an
optional **Experience** entry. Every technical claim below was checked against the
repository (`apps/api/requirements`, `apps/ai-service/requirements`,
`docker-compose.yml`, `apps/web/package.json`) — nothing here describes a feature
that does not exist in the code.

---

## 1. About section — full version

> Use this one if you want the project to carry real weight on your profile.
> LinkedIn's About field allows **2,600 characters**; this is well inside it.
>
> ```
> I build AI that answers business questions — and shows its work.
>
> Most organizations sit on answers they can't reach. The number lives in a
> database, the policy lives in a PDF, and the person who needs both waits on a
> ticket. Closing that gap safely is the work I care about.
>
> DataForge AI is the product I'm building. You ask a question in plain language,
> and it answers with read-only SQL run against your connected databases, plus
> citations from your own documents.
>
> Four decisions shape it, and all four are about trust:
>
> • Read-only by default. Every query is parsed to an AST and validated before it
> runs, so statement classification can't be evaded with comments or whitespace.
> The model never gets unrestricted database access.
>
> • Grounded, not guessed. Answers point back to the tables that were queried and
> the document passages that were cited, so anyone can verify a result in seconds.
>
> • Scoped to the person asking. Role-based permissions decide which data sources
> and documents each teammate can reach.
>
> • Audited end to end. Every run is recorded with the tools it used, its model,
> tokens and duration, in an append-only log that cannot be edited or deleted.
>
> That last point is the difference between a demo and something you can put in
> front of a CFO. In this space trust isn't a feature — it's the product.
>
> The stack: Django 5 and DRF over ASGI (Daphne + Channels) for the platform, a
> separate Flask service for the analyst and RAG pipeline, PostgreSQL 16 with
> pgvector for document retrieval, Celery and Redis for async work, and a
> Next.js 15 / React 19 / TypeScript front end — six services on one
> docker compose up.
>
> I'm glad to talk with teams still answering the same questions by hand, and with
> engineers building retrieval and agent systems that have to be trustworthy
> rather than just clever.
>
> → data-forge.ai
> ```

**Length: 1,837 characters** (763 to spare under the 2,600 limit).

---

## 2. About section — short version

> For a tighter profile, or if you keep work history in the Experience section
> instead.
>
> ```
> Most organizations sit on answers they can't reach — the number is in a
> database, the policy is in a PDF, and the person who needs both waits on a
> ticket.
>
> I build DataForge AI to close that gap safely. Ask a question in plain
> language and get read-only SQL against your connected databases, plus answers
> cited from your own documents. Queries are AST-validated before they run,
> access is scoped by role, and every AI run lands in an append-only audit log
> you can't quietly edit.
>
> In this space trust isn't a feature — it's the product.
>
> Stack: Django + DRF over ASGI, a Flask AI service, PostgreSQL with pgvector,
> Celery and Redis, Next.js 15 / React 19 / TypeScript, Docker Compose.
>
> → data-forge.ai
> ```

**Length: 701 characters.**

---

## 3. Featured section card

Add the project under **Featured** so the link and the video sit on your profile
visually, not just in text.

- **Title:** `DataForge AI — ask your business data anything`
- **Description:**

  > Plain-language questions become read-only SQL over your connected databases
  > and cited answers from your own documents — scoped by role and recorded in an
  > append-only audit log.
  >
  > 34-second product tour. Trust isn't a feature here; it's the product.

- **Media:** upload [dataforge-linkedin-promo.mp4](dataforge-linkedin-promo.mp4)
  (or set its thumbnail to
  [linkedin-square-1080x1080.png](linkedin-square-1080x1080.png)).
- **Link:** `https://data-forge.ai`

---

## 4. Optional Experience entry

If you list DataForge AI as a role:

- **Title:** `Founder & Engineer` (or `Software Engineer — DataForge AI`)
- **Description:**

  > Building an AI analyst that answers business questions from connected
  > databases and internal documents — with read-only SQL enforced by AST
  > validation, role-scoped access, and a tamper-evident audit trail for every run.
  >
  > Django + DRF over ASGI, a separate Flask AI/RAG service, PostgreSQL with
  > pgvector, Celery + Redis, Next.js 15 / React 19. Six services, one Docker
  > Compose stack.

---

## How to paste it in

1. **About:** Profile → *Edit profile* → **About** → *Edit* → paste version 1 → Save.
   Keep the first line as the hook; LinkedIn hides the rest behind "…see more"
   after roughly three lines.
2. **Featured:** Profile → *Add profile section* → **Recommended → Add featured**
   → *Add a link* → fill in the title and description above.
3. **Cover banner:** swap your profile/company cover for
   [linkedin-cover-1584x396.png](linkedin-cover-1584x396.png) so the profile
   visually matches the copy.

## Before you publish — three things to decide

- **Your role.** The copy says "the product I'm building." If you contribute
  rather than lead it, change that to "the product I work on" and drop the
  first-person singular from the four bullets.
- **The link.** `data-forge.ai` is used throughout. Swap it for your real
  destination — or a UTM-tagged link so you can see profile traffic — if it
  differs.
- **Metrics.** There are deliberately none. No users, revenue, accuracy or
  benchmark numbers appear anywhere, because none were verifiable from the repo.
  Add real ones only when you have them to back up; a specific number you can
  defend is worth more than an impressive one you can't.
