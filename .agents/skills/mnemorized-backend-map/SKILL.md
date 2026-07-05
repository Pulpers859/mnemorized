---
name: mnemorized-backend-map
description: Architecture map of the Mnemorized FastAPI backend — layout invariants, auth and demo-bypass semantics, quota reservation mechanics, env var effects, and provider transport quirks. Use before editing backend/app or when debugging auth, quota, persistence, or provider behavior.
---

# Mnemorized Backend Map

Ground-truth backend invariants, verified 2026-07. File/function names are durable; exact line numbers are not.

## Layout invariants

- All routes live in `backend/app/main.py`; `backend/app/config.py` owns every `os.getenv` call (grep-confirmed single source of truth for env); `backend/app/auth.py` verifies Supabase JWTs against the project JWKS (cached 1 hour).
- `app.mount("/", StaticFiles(...))` is the **last statement in main.py and must stay last** — moving it earlier swallows every `/api/*` route.
- `.env` is parsed by a hand-rolled loader (not python-dotenv). Placeholder-looking values (`replace-with…`, `your-project-ref…`) are treated as UNSET silently — copy-pasted example values degrade to "not configured" instead of erroring.

## Auth semantics

- `DEMO_AUTH_BYPASS` **defaults to True**. In dev (`APP_ENV != production`) provider proxy endpoints accept anonymous calls (quota is a no-op for anonymous users). Production ignores the bypass entirely. This is intentional demo behavior — do not "fix" it.
- The bypass affects only provider proxy endpoints. Palace/catalog-write/audio persistence always requires a signed-in Supabase user (401 without a token).
- Admin = plain email allowlist from `ADMIN_EMAILS` CSV; there is no DB admin flag. Empty allowlist → all admin endpoints 403 for everyone.
- User-table access forwards the caller's JWT to Supabase so RLS enforces ownership; admin/catalog-seed/medical paths use the service-role key and bypass RLS entirely.

## Quota mechanics

- Plans: free 40 / pro 400 / team 4000 requests per calendar month (env-tunable); enterprise/unlimited uncapped. A dev plan-override file (`backend/dev_data/plan_overrides.json`) silently masks the real subscription — check it when quota behavior looks wrong locally.
- Reservation is optimistic in an **in-process 60s cache** before the paid provider call, released on failure. The durable count is `usage_events` rows written on success by a fire-and-forget background task that swallows exceptions. Consequences: quota is per-worker-process (not global under horizontal scaling), concurrent cold-cache requests can race past the limit, and systematic Supabase write failures cause silent quota drift.
- Exhaustion returns HTTP 402 with a `quota_exceeded` body including plan/usage/billing info.
- Rate limiting is an in-memory sliding window per user/IP; it resets on every restart and is not shared across workers.

## Provider quirks

- Anthropic proxy merges the `anthropic-beta` header with the payload `betas` field. If `x-evidence-grounding: true` + `x-evidence-topic` headers are present and medical knowledge is configured, retrieved medical chunks are **silently appended to the system prompt server-side** — a request-mutating side channel to know about when debugging prompt behavior.
- Gemini uses two different auth transports: text/prompt-director sends the key as `?key=` query param; image generation sends `x-goog-api-key` header. One can break without the other. `/api/diagnose-gemini` probes three auth styles (admin-only in prod).
- Error mapping is inconsistent by design-drift: Anthropic/Gemini collapse upstream failures to 502/504; ElevenLabs passes the upstream status code through verbatim.
- ElevenLabs voice lookup: an unrecognized `ELEVENLABS_DEFAULT_VOICE` name silently falls back to a hardcoded Rachel voice ID.
- Usage is double-logged: JSONL at `backend/logs/anthropic_usage.jsonl` plus `usage_events` rows in Supabase.

## Persistence semantics

- `palace_versions` is append-only: every save inserts version `latest+1`; nothing prunes old versions (unbounded growth is known/accepted).
- First-save failure cleanup (`_delete_empty_palace_best_effort`) is fire-and-forget — orphaned empty palace rows are possible and non-fatal.
- Audio lives in Supabase Storage bucket `palace-audio` at `{user_id}/{palace_id}/{filename}`; ownership is enforced only by Storage RLS on the first path segment.

## Known soft spots (verified 2026-07, intentionally not yet fixed)

- `/api/medical-knowledge/coverage` has no auth gate (only requires service-role config) — any client can enumerate medical source titles/tags.
- Quota enforcement is per-process (see above) — acceptable at single-instance scale, revisit before scaling out.
- Confirm with Patrick before "fixing" anything in this section; these are recorded so future agents don't rediscover them as surprises.
