# TasksDAV

CalDAV façade over **Google Tasks** (source of truth). Connect Google → copy URL → use Errands / Apple Reminders / DAVx5.

See [SPEC.md](./SPEC.md) for the contract. Multi-tenant security notes: [docs/security.md](./docs/security.md). Brand: [DESIGN.md](./DESIGN.md).

## Quick start (Compose)

```bash
cp .env.example .env   # set SECRET_KEY + Google OAuth
docker compose up --build
```

Open http://127.0.0.1:8080 → **Connect Google Tasks** → copy CalDAV credentials.

Local API without Compose:

```bash
cd backend
cp ../.env.example .env
uv sync
uv run uvicorn app.main:app --reload --app-dir . --port 8010
```

### Google Cloud

1. OAuth client type: **Web application**
2. Redirect: `{BASE_URL}/auth/google/callback`
3. Enable **Google Tasks API**

## Stack

- FastAPI + SQLAlchemy
- Postgres via **Docker Compose** (local) or **Neon** (hosted)
- Thin connect UI (`frontend/index.html`)
- Container image via **GitHub Actions → GHCR**

## Field support (MVP)

| Field | Supported |
|-------|-----------|
| Title | yes |
| Description / notes | yes |
| Due **date** | yes (no time) |
| Complete | yes |
| One-level subtasks | yes |
| Arbitrary links | read-only from Google |

## Container

```bash
# published by CI to ghcr.io/<owner>/tasksdav
docker pull ghcr.io/<owner>/tasksdav:latest
```

Workflow: `.github/workflows/container.yml` builds on `main` / tags.

## Neon (optional instead of Compose db)

Set `DATABASE_URL` to the Neon **pooled** URL (`postgresql+asyncpg://…?ssl=require`). You can run only the `app` service, or point Compose `app` at Neon and stop `db`.

## Layout

```
tasksdav/
  Dockerfile
  docker-compose.yml
  api/index.py
  frontend/index.html
  backend/app/
  docs/security.md
```
