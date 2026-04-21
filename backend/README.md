# Mnemorized Backend

This backend is the first architectural layer between the browser and Anthropic.

It gives you:

- Server-side Anthropic key storage instead of `localStorage`
- Real app routes served from the backend: `/`, `/forge`, and `/library`
- A stable proxy endpoint for the forge UI
- Basic per-IP rate limiting
- Request/usage logging for future analytics and billing
- Supabase-aware user context on proxied AI requests
- Authenticated usage event persistence into Supabase `usage_events`
- Plan-aware monthly request quota enforcement before Anthropic is called
- Clean extension points for auth, persistence, and subscriptions

## Endpoints

- `GET /api/health`
- `GET /api/config/public`
- `GET /api/account/summary`
- `POST /api/anthropic/messages`

## Local Run

1. Create a virtual environment if you want one.
2. Install dependencies:

```powershell
python -m pip install -r backend/requirements.txt
```

3. Copy `backend/.env.example` to `backend/.env` and set `ANTHROPIC_API_KEY`.
4. If you want auth + saved palaces, also set `SUPABASE_URL` and `SUPABASE_ANON_KEY`.
5. Optional: tune `FREE_MONTHLY_REQUESTS`, `PRO_MONTHLY_REQUESTS`, and `TEAM_MONTHLY_REQUESTS` for plan enforcement.
6. Start the server:

```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Or on Windows:

```powershell
.\backend\start.ps1
```

7. Open the served app routes:

```text
http://127.0.0.1:8000/
http://127.0.0.1:8000/forge
http://127.0.0.1:8000/library
```

## Logging

Proxy usage events are appended to:

- `backend/logs/anthropic_usage.jsonl`

This is intentionally lightweight for now. In phase 2, those records can move into Postgres and attach to authenticated users.
