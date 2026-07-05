---
name: mnemorized-deploy-check
description: Review Mnemorized deployment configuration — the single Render service, env var wiring, provider model pinning, and prod/dev divergence risks. Use when touching render.yaml, env examples, or rotating provider models.
---

# Mnemorized Deploy Check

Ground truth verified 2026-07 against `render.yaml`.

## Shape

- One Render web service `mnemorized` (free plan, Python 3.12.3). Build: `pip install -r backend/requirements.txt`. Start: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`.
- The same service serves the API and all static pages — there is no separate static site or CDN.
- CI (`.github/workflows/ci.yml`) runs compileall + pytest on pushes/PRs but does not gate Render deploys. Run `mnemorized-validation` before pushing to main. (Whether Render auto-deploys on push is UNVERIFIED from the repo — confirm in the Render dashboard before relying on it.)

## Env vars

- Dashboard-managed secrets (`sync: false`): `APP_BASE_URL`, `ANTHROPIC_API_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `CORS_ORIGINS`, `ADMIN_EMAILS`.
- Pinned values in render.yaml: `APP_ENV=production`, `ANTHROPIC_TIMEOUT_SECONDS=180`, `ANTHROPIC_MAX_TOKENS=8192`, `SUPABASE_JWT_AUDIENCE=authenticated`, `GEMINI_MODEL`/`GEMINI_TEXT_MODEL`/`GEMINI_IMAGE_MODEL`, `OPENAI_EMBEDDING_MODEL`, `TRUST_PROXY_HEADERS=true`, `BILLING_MODE=beta`.

## Traps

- **Model rotation**: Gemini/OpenAI model names are pinned in BOTH render.yaml and the backend defaults in `backend/app/config.py`. Rotating a model means updating both, or prod and local silently diverge.
- `OPENAI_EMBEDDING_DIMENSIONS` must match the `vector(1536)` column in the Supabase schema — changing it requires a DB migration, not just an env edit.
- Prod is fail-closed: `APP_ENV=production` disables `DEMO_AUTH_BYPASS`; missing `CORS_ORIGINS` with no `APP_BASE_URL` yields **zero** allowed origins and browser calls fail silently.
- Rate limiting and quota reservation are in-memory per process — scaling to multiple workers or instances weakens quota enforcement (see `mnemorized-backend-map`).
- `TRUST_PROXY_HEADERS=true` is required on Render or all clients rate-limit-bucket under one IP.
