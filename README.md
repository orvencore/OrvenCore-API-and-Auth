# OrvenCore API and Auth

Central FastAPI backend for OrvenCore authentication, authorization, user identity, and integrations.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

The development default uses SQLite at `./orvencore.db`. Production should set `DATABASE_URL` to PostgreSQL.

Run migrations:

```bash
alembic upgrade head
```

Run with Docker:

```bash
docker compose up --build
```

## First Endpoints

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/refresh`
- `GET /auth/me`
- `GET /permissions/me`
- `GET /discord/users/{discord_user_id}`
- `PUT /discord/me`

Swagger docs are available at `/docs` while the app is running.
