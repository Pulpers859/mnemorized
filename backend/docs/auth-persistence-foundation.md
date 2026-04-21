# Auth + Persistence Foundation

The proxy is the first permanent backend surface. The next layer should attach identity and storage to it rather than building a separate parallel backend.

## Recommended stack

- Supabase Auth for sign-in
- Supabase Postgres for persisted palaces and history
- The existing FastAPI proxy for AI calls, usage metering, and subscription checks

## Suggested phase 2 flow

1. Browser signs in with Supabase.
2. Browser sends Supabase access token to FastAPI on every non-public request.
3. FastAPI verifies the JWT, resolves the user, and tags every proxy call and save event with `user_id`.
4. Palace outputs are saved as durable records instead of living only in page state.
5. Billing gates usage inside the backend before Anthropic is called.

## Minimum entities

- `profiles`: per-user metadata
- `palaces`: top-level saved memory palaces
- `palace_versions`: immutable snapshots of each generated version
- `usage_events`: proxy events tied to users for billing and analytics
- `subscriptions`: current plan and Stripe linkage

## UI impact

- Replace anonymous "generate only" mode with signed-in sessions
- Add save/load actions in the forge
- Add a personal library page backed by `palaces`
- Keep the current operator/debug tooling behind authenticated staff controls later

## Backend integration points already prepared

- `/api/anthropic/messages` is the future enforcement point for quotas and plans
- Usage logging already records request metadata
- Authenticated proxy requests can now also persist `usage_events` into Supabase
- Health checks already advertise auth and persistence as planned foundations
