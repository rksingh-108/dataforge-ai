# Redis

Redis is a single dependency serving three distinct logical databases. They are
kept separate so a backlog of Celery work cannot evict the channel-layer state
used for WebSocket delivery.

| Database | URL                          | Used for                                   |
| -------- | ---------------------------- | ------------------------------------------ |
| `0`      | `REDIS_URL`                  | Django cache + Channels channel layer      |
| `1`      | `CELERY_BROKER_URL`          | Celery task broker (document processing)   |
| `2`      | `CELERY_RESULT_BACKEND`      | Celery result backend                      |

## Operational notes

- `appendonly yes` is enabled in `docker-compose.yml` so a restart does not lose
  queued work.
- There is **no authentication** in the local stack; Redis is only reachable on
  the internal Docker network. A production deployment must set `requirepass`
  and place Redis on a private network — tracked in
  `security/vulnerability-management/README.md`.
- Redis is treated as **non-authoritative**: losing it degrades background
  processing and realtime updates but never loses platform data, which lives in
  PostgreSQL.
