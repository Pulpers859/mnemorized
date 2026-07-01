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
- Private, service-role-only medical knowledge retrieval for future quality gates
- Clean extension points for auth, persistence, and subscriptions

## Endpoints

- `GET /api/health`
- `GET /api/config/public`
- `GET /api/account/summary`
- `POST /api/medical-knowledge/context`
- `POST /api/medical-knowledge/quality-check`
- `POST /api/anthropic/messages`
- `POST /api/generate-image`

## Local Run

1. Create a virtual environment if you want one.
2. Install dependencies:

```powershell
python -m pip install -r backend/requirements.txt
```

3. Copy `backend/.env.example` to `backend/.env` and set `ANTHROPIC_API_KEY`.
4. If you want auth + saved palaces, also set `SUPABASE_URL` and `SUPABASE_ANON_KEY`.
5. If you want admin catalog publishing, set `SUPABASE_SERVICE_ROLE_KEY` and `ADMIN_EMAILS`.
6. If you want private medical knowledge retrieval, set `SUPABASE_SERVICE_ROLE_KEY` and `OPENAI_API_KEY`.
7. Optional: tune `FREE_MONTHLY_REQUESTS`, `PRO_MONTHLY_REQUESTS`, and `TEAM_MONTHLY_REQUESTS` for plan enforcement.
8. Start the server:

```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8001 --reload
```

Or on Windows:

```powershell
.\tools\Start-Mnemorized-App.ps1
```

9. Open the served app routes:

```text
http://127.0.0.1:8001/
http://127.0.0.1:8001/forge
http://127.0.0.1:8001/library
```

## Logging

Proxy usage events are appended to:

- `backend/logs/anthropic_usage.jsonl`

This is intentionally lightweight for now. In phase 2, those records can move into Postgres and attach to authenticated users.

## Private Medical Knowledge

Run the medical SQL block in `backend/sql/supabase_schema.sql` before retrieval. It creates a private `medical` schema, RLS-hardened source/chunk tables, vector search indexes, and service-role-only RPC functions.

Local ingestion is handled by:

```powershell
python tools\ingest_medical_knowledge.py --source-dir "C:\Users\Patrick's Computer\OneDrive - WV School of Osteopathic Medicine\Desktop\Files need moved to USB\TinTin Chapters" --dry-run --limit-files 1
python tools\ingest_medical_knowledge.py --source-file "C:\Users\Patrick's Computer\OneDrive - WV School of Osteopathic Medicine\Desktop\Files need moved to USB\TinTin Chapters\Tintin_Endocrine.pdf" --confirm-send-to-openai
```

Actual ingestion sends chunk text to OpenAI for embeddings, so the script refuses to run unless you explicitly add `--confirm-send-to-openai`. Browser endpoints return citation metadata and short excerpts only; full source chunks remain backend/database-side.

After a pilot ingestion, run retrieval QA without printing private source chunks:

```powershell
python tools\qa_medical_retrieval.py
```

## Repo Layout Note

The backend serves routed HTML from `frontend/pages/` and static PWA assets from `frontend/`. Keep root-level runtime clutter out of the repo root unless a deployment tool explicitly requires it.
