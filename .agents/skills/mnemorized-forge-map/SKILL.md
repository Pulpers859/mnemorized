---
name: mnemorized-forge-map
description: Architecture map of the Mnemorized forge workspace — external script files, stage numbering, in-memory state model, API retry patterns, and fragility hotspots. Use before editing forge behavior, the guided lesson flow, or any file in frontend/scripts/.
---

# Mnemorized Forge Map

Ground-truth architecture of the forge surface, verified 2026-07. Read this before editing forge behavior; re-verify anything marked volatile.

## Where the logic lives

- `frontend/pages/forge.html` (~2,240 lines) contains **no inline JS** — only inline CSS plus `<script src>` tags at the bottom. Editing forge behavior means editing `frontend/scripts/forge-*.js`, never the HTML.
- Load order (must be preserved; `forge-state.js` first, everything depends on it):
  1. `palace-api.js` — shared fetch wrapper + palace/catalog/admin API namespaces (also used by library and admin pages)
  2. `forge-state.js` — globals, model IDs, Advisor config, `claudeFetch` proxy wrapper, backend-status modal
  3. `forge-auth.js` — Supabase client init, session, sign-in/out
  4. `forge-upload.js` — Stage 0 document intelligence (optional PDF/doc → concepts → `#topic` textarea)
  5. `forge-input-builder.js` — guided input builder; writes into the same `#topic` textarea so the pipeline is unaware of it
  6. `forge-pipeline.js` — core story → quality → image-prompt pipeline, image generation, bundle export
  7. `forge-guided.js` — guided lesson: anchor coords, TTS, vision auto-anchor placement, video export, one-click orchestrator

## Stage numbering trap

The UI shows three numbered stages, but commits and internal labels use a 0–7 logical numbering. They do not match:

- UI stage 01 "Memory Palace Scene" = internal attempt label `stage2-story-script-*` in `forge-pipeline.js`
- UI stage 02 = Medical Quality Gate (requires sign-in + medical retrieval)
- UI stage 03 = Scene Illustration (image prompts + generation)
- Logical Stage 0 = document upload; Stage 5 = audio storage; Stage 6 = video export; Stage 7 = one-click guided lesson + vision auto-anchor
- When a commit message or task says "Stage N", confirm which numbering it means before editing.

## State model

- There is **no app-owned localStorage/sessionStorage anywhere**. All forge state is in-memory JS; a page refresh loses the entire in-progress palace (script, images, audio, coords). Only an explicit Save persists, via `/api/palaces/save`.
- Key objects: `backendState` (forge-state.js, drives the connection modal), `authState` (forge-auth.js, Supabase session), guided `state` (forge-guided.js: story, segments, coords, audio blob/paths).
- `forgeReplayMode` (`live`/`record`/`replay` in forge-state.js) changes request headers — a QA/replay harness; check it before assuming a call hit a live provider.

## API and retry conventions

- `claudeFetch()` in forge-state.js: 401 → opens auth modal; 402 → quota-exceeded message built from `payload.billing`/`usage`; network failure → connection modal.
- Standard pattern: first 401 → refresh Supabase token → retry exactly once, then give up. This is copy-pasted (with drift) in forge-pipeline.js and forge-guided.js — if you change one instance, audit the others.
- Advisor tool: `withAdvisor()` in forge-state.js injects the Opus advisor model + beta header. Used for medical context and story generation only — **not** for image prompts or vision-coordinate calls.

## Fragility hotspots

- All JS↔HTML coupling is via `document.getElementById` on ids in forge.html (`#stage-story`, `#topic`, `#guided-one-click-btn`, …). Renaming or restructuring HTML silently breaks JS with no compile-time check — grep the id across frontend/scripts before touching it.
- `runPipeline()` in forge-pipeline.js is a ~540-line function interleaving demo-mode branching, retry loops, and UI status updates; retry eligibility is keyed to exact strings (e.g. `stop_reason === 'max_tokens'`).
- Image-prompt composition has four near-duplicate builders plus a Gemini-director → Claude-composer fallback chain in forge-pipeline.js — updating one path and forgetting the others is the classic regression here.
- `oneClickLesson()` in forge-guided.js hard-chains buildPlan → autoPlaceAnchors → generateAudio with no partial-failure recovery; a mid-chain failure leaves partial state.
- Cache busting: bump the `?v=` query on the script tag when changing any forge-*.js (browser HTTP cache). The service worker cache name (`mnemorized-v*` in frontend/sw.js) must be bumped on cache-shape changes. The SW is registered only by landing and library pages, not forge or admin.
- Shared shell breakpoint is 760px (app-shell.css) but forge-local CSS uses 600px — they are not unified; test both widths.
