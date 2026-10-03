# Local Setup

Two paths: **Docker (recommended)** gets everything running in one command;
**native** is for working on a single service with fast reloads.

## Prerequisites

| Tool | Version | Notes |
| ---- | ------- | ----- |
| Docker Desktop | Recent, with Compose v2 | Required for the container path |
| Python | 3.13 or 3.14 | API and AI service |
| Node.js | 22 | Frontend |
| Git | Any recent | |

You do **not** need Postgres, Redis or an LLM API key to run the tests.

## Path A — Docker (recommended)

```bash
git clone <repo> && cd dataforge-ai
cp .env.example .env
```

Now fill in `.env`. The two values you must generate:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"                                  # DJANGO_SECRET_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"      # DATAFORGE_FERNET_KEY
python -c "import secrets; print(secrets.token_urlsafe(40))"                                   # INTERNAL_SERVICE_TOKEN
```

Start everything:

```bash
docker compose up --build
```

Then seed the development organization (first run only):

```bash
docker compose exec api python manage.py seed_development
```

### What the seed creates

Idempotent — running it repeatedly changes nothing. Requires `DEBUG=true`.

| Email | Role | Password |
| ----- | ---- | -------- |
| `owner@dataforge.local` | Owner | `DataForge!Dev1` |
| `admin@dataforge.local` | Admin | `DataForge!Dev1` |
| `analyst@dataforge.local` | Analyst | `DataForge!Dev1` |
| `viewer@dataforge.local` | Viewer | `DataForge!Dev1` |

All four belong to **DataForge Demo Organization**. The password is intentionally
public: the command refuses to run unless `DEBUG` is on.

Sign in at <http://localhost:3000/login>.

### Service URLs

| Service | URL | Health |
| ------- | --- | ------ |
| Web | http://localhost:3000 | `/` |
| API | http://localhost:8000/api/v1/ | http://localhost:8000/_health/ |
| AI service | http://localhost:8001 | http://localhost:8001/_health/ |
| Postgres | localhost:5432 | `pg_isready` |
| Redis | localhost:6379 | `redis-cli ping` |

## Windows quick start — `START.bat` and `STOP.bat`

On Windows you do not have to remember the Compose commands. Two batch files at
the repository root wrap the same `docker compose` configuration used by the
Makefile, so a developer (or an intern) can start and stop the whole environment
by double-clicking a file or running one command.

### `START.bat`

```bat
START.bat
```

**What it starts:** the complete development stack from `docker-compose.yml` —
`db` (PostgreSQL + pgvector), `redis`, `api`, `worker` (Celery), `ai-service` and
`web`. The `api` container applies migrations on start.

**Prerequisites**

1. **Docker Desktop installed and running.** The script checks for the `docker`
   binary, the daemon and the Compose v2 plugin, and tells you exactly which one
   is missing if it stops.
2. A `.env` file in the repository root. If it is missing, the script copies
   `.env.example` to `.env`, warns you that the values are placeholders, and exits
   so you can fill in the secrets before the first start — it never generates or
   prints a secret. Fill in at least `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`,
   `DATAFORGE_FERNET_KEY` and `INTERNAL_SERVICE_TOKEN` (see the top of this page
   for the generator commands).

**What to expect**

- Six numbered progress steps (`[1/6]` … `[6/6]`) with clear status lines.
- `db` and `redis` are waited on until their Docker healthchecks report healthy.
- `api` is waited on until `GET /_health/` answers `200` — on a cold database this
  includes running migrations, so it can take a little while.
- Running it again while the stack is already up is safe: it reports that it is
  reusing the running services and refreshes them. It is idempotent.
- If startup fails, it prints the current service status and the last 40 log lines
  before exiting non-zero, so the failure is diagnosable from the terminal.

**Local URLs once it prints "Development environment is READY"**

| Service | URL |
| ------- | --- |
| Web application | http://localhost:3000 |
| API root | http://localhost:8000 |
| API health | http://localhost:8000/_health/ |
| AI service health | http://localhost:8001/_health/ |

Sign in at http://localhost:3000/login after seeding with
`docker compose exec api python manage.py seed_development`.

> The AI service needs `LLM_API_KEY` / `EMBEDDING_API_KEY` in `.env` to answer
> analyst questions. The stack starts and every other feature works without them;
> analyst runs fail with a clear error until they are set.

### `STOP.bat`

```bat
STOP.bat
```

**What it stops:** the same six services, using `docker compose stop`. It is the
least destructive way to shut the environment down.

**What it preserves:** everything that holds data. It does **not** delete source
code, Docker volumes, or persistent development data — your PostgreSQL database,
Redis data and uploaded documents under the `media` volume all survive.

**When to use it:**

- At the end of the day, or before shutting down your machine, to free memory.
- Before switching to another project that needs the same ports (3000/8000/8001/5432/6379).
- Any time you want the stack off but your seeded data kept for next time.

Running it when nothing is up is safe: it reports that nothing is running and
exits successfully. To *reset* the environment instead — deleting all data — use
an explicit destructive command such as `docker compose down -v` or `make clean`;
`STOP.bat` never does that.

## Path B — Native (per service)

### Backend

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r apps/api/requirements/dev.txt
docker compose up -d db redis                          # platform dependencies in containers
cd apps/api
python manage.py migrate
python manage.py seed_development
python manage.py runserver                             # http://localhost:8000
```

Run the API as ASGI when you need WebSockets:

```bash
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

Celery worker (document processing):

```bash
cd apps/api && celery -A config worker -l info
```

### AI service

```bash
python -m venv .venv-ai && source .venv-ai/bin/activate
pip install -r apps/ai-service/requirements/dev.txt
cd apps/ai-service
flask --app wsgi run --port 8001        # or: gunicorn --bind 0.0.0.0:8001 wsgi:app
```

Requires at least `INTERNAL_SERVICE_TOKEN` and `INTERNAL_API_BASE_URL`
(`http://localhost:8000` for native). It will start without an LLM key, but any
agent run will fail at the provider call — that is expected and is a real error,
not a stub.

### Frontend

```bash
cd apps/web
npm install
API_BASE_URL=http://localhost:8000 npm run dev     # http://localhost:3000
```

`API_BASE_URL` is **server-side only**; the browser always calls the BFF.

## Running tests

```bash
make test-backend    # spins up a throwaway Postgres+pgvector if needed
make test-ai
make test-web
make test-security
make test            # all of the above
```

Backend tests need a real PostgreSQL with pgvector (the schema uses vector
columns). `make test-backend` starts a temporary container on port 55432 and
removes it afterwards. To use an existing database instead, set `TEST_DB_HOST`,
`TEST_DB_PORT`, `TEST_DB_USER`, `TEST_DB_PASSWORD`, `TEST_DB_NAME`.

## Common tasks

```bash
make help              # list every target
make migrate
make makemigrations
make seed
make db-shell
make logs
make lint
make security
make clean             # DESTROYS local data
```

## Troubleshooting

See [debugging.md](debugging.md). The most common issues:

| Symptom | Cause | Fix |
| ------- | ----- | --- |
| `port is already allocated` | Something else uses 5432/6379/3000/8000/8001 | Set `*_HOST_PORT` in `.env`, or stop the other process |
| `RuntimeError: DATAFORGE_FERNET_KEY is not configured` | Missing key | Generate one (above) and restart |
| Login returns 401 but credentials are right | Seed never ran | `docker compose exec api python manage.py seed_development` |
| API container exits on start | Migrations failed | `docker compose logs api` |
| AI runs fail with `provider_error` | No/invalid `LLM_API_KEY` | Set a key, or point `LLM_BASE_URL` at a local OpenAI-compatible server |
| `psycopg` build error on native install | Missing libpq | Use the Docker path, or install libpq (`brew install libpq` / `apt install libpq-dev`) |
