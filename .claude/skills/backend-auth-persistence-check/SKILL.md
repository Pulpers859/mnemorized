---
name: backend-auth-persistence-check
description: Review auth, Supabase persistence, account summary, library save/load, and saved-palace data changes in the Mnemorized FastAPI backend.
---

# Backend Auth Persistence Check

Use this when work touches auth context, Supabase config, saved palaces, account summary, library routes, or persistence helpers.

For the full invariant list (demo-bypass semantics, static-mount ordering, RLS vs service-role paths, append-only versioning), load `mnemorized-backend-map` first.

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
   - `DEMO_AUTH_BYPASS` (defaults true; dev-only, provider endpoints only) is not "fixed" as a bug and persistence endpoints still require sign-in
   - the `app.mount("/", StaticFiles(...))` line stays the last statement in `main.py`
   - user-scoped queries keep forwarding the caller's JWT (RLS); service-role usage stays limited to admin/catalog-seed/medical paths
4. For schema or API-shape changes, update docs or examples only when behavior truly changed.
5. Validate with `python -m compileall backend`; run the server when practical.

## Avoid

- reading or staging `backend/.env`
- silently turning persistence failures into local-only success
- broad database redesign when a route-level fix is enough

