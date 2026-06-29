---
name: backend-auth-persistence-check
description: Review auth, Supabase persistence, account summary, library save/load, and saved-palace data changes in the Mnemorized FastAPI backend.
---

# Backend Auth Persistence Check

Use this when work touches auth context, Supabase config, saved palaces, account summary, library routes, or persistence helpers.

## Workflow

1. Identify the backend surface involved:
   - `backend/app/auth.py`
   - `backend/app/config.py`
   - `backend/app/main.py`
   - Supabase SQL or persistence docs
2. Trace the request path from browser to FastAPI to Supabase.
3. Check:
   - missing Supabase config degrades clearly
   - authenticated and anonymous modes are distinct
   - saved palace records keep stable ownership and version semantics
   - failed saves/loads return explicit errors
   - example env files stay placeholder-only
4. For schema or API-shape changes, update docs or examples only when behavior truly changed.
5. Validate with `python -m compileall backend`; run the server when practical.

## Avoid

- reading or staging `backend/.env`
- silently turning persistence failures into local-only success
- broad database redesign when a route-level fix is enough

