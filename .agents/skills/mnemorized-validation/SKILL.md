---
name: mnemorized-validation
description: Run and honestly report Mnemorized validation — compile check, pytest suite, server smoke, and browser stress — and know what each layer does and does not prove. Use before commits, after backend or forge changes, or before claiming something works.
---

# Mnemorized Validation

## Standard command

```powershell
powershell -File tools/Invoke-MnemorizedValidation.ps1 -Tests -SmokeServer
```

- Always runs `python -m compileall backend`.
- `-Tests` runs `python -m pytest tests`.
- `-SmokeServer` starts uvicorn on port 8001 (override with `-Port`), polls `/api/health` up to 30s, curls `/`, `/forge`, `/library`, `/api/health`, then kills the server.
- Run the pytest step in a sonnet subagent for long sessions (session cost protocol).

## What the suite covers

- `tests/test_palace_api.py` — palace list/save/versioning, profile upsert, bearer-token requirements, catalog publish fail-closed without service role, admin diagnostics, medical quality-check citation suppression.
- `tests/test_provider_and_static_boundaries.py` (largest) — env-file handling, CORS, dev demo-bypass vs prod fail-closed, quota-exceeded safety, Gemini 502 handling, advisor tool/beta passthrough, oversized-request rejection, plus **static HTML assertions** (inline handler escaping, service-worker cache rules, env-example placeholders). Frontend edits can fail backend-suite tests — run the suite even for "frontend-only" changes.
- `tests/test_visual_qa_pack.py` — unit tests for `tools/visual_qa_pack.py`.

## What nothing covers

- **There is no CI** (no `.github/workflows`) — local runs are the only enforcement; never assume main is green because it was pushed.
- No E2E browser tests in pytest. `tools/run_forge_browser_stress.mjs` (Playwright) is separate, and falls back to importing Playwright from gitignored `local_archive/playwright-runner/node_modules` — it breaks on a fresh clone/machine unless Playwright is installed normally.

## Honest reporting rules

- compileall + pytest passing ≠ provider validation. Provider-generation claims require real local or hosted API keys actually exercised.
- Static HTML test assertions ≠ real browser behavior. Say "correct-by-inspection" when no browser was driven.
- Always state which layers ran: compile / pytest / smoke / browser / live provider.
