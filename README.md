# Mnemorized

Mnemorized is a web app for generating visual medical memory palaces, saving them to a Supabase-backed library, and routing AI provider calls through a FastAPI backend.

The browser uses Supabase Auth for sessions, while profile sync and saved-palace CRUD are routed through FastAPI under `/api/profile/ensure` and `/api/palaces` so ownership, versioning, and persistence errors have one backend contract.

## Source Of Truth

- Active repo: `C:\Dev\Mnemorized`
- GitHub remote: `https://github.com/Pulpers859/mnemorized.git`
- Current tracked branch: `main`
- Previous OneDrive/Desktop copy: stale transitional copy after the June 29, 2026 migration
- Ignored support archive: `C:\Dev\Mnemorized\local_archive\2026-06-29`

## Project Structure

```text
backend/                 FastAPI app, provider proxy, auth, quota, persistence helpers
frontend/
  pages/                 Routed HTML pages served by FastAPI
  assets/                Runtime image assets used by the PWA manifest and pages
  styles/                Shared app-shell visual system overrides
docs/                    Product, architecture, and workflow notes
tools/                   Standalone local support tools and Claude launcher
render.yaml              Render deployment configuration
```

## Local Run

```powershell
python -m pip install -r backend/requirements.txt
Copy-Item backend\.env.example backend\.env
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8001 --reload
```

Or use the Windows launcher, which installs requirements, chooses an available local port,
starts the backend, and opens Forge:

```powershell
.\tools\Start-Mnemorized-App.ps1
```

Open:

- `http://127.0.0.1:8001/`
- `http://127.0.0.1:8001/forge`
- `http://127.0.0.1:8001/library`

## Configuration

Real local secrets live in ignored `backend/.env`. Keep `backend/.env.example` placeholder-only.

Important variables:

- `ANTHROPIC_API_KEY`
- `GEMINI_API_KEY`
- `GEMINI_TEXT_MODEL` for constitution-guided prompt direction, default `gemini-3.1-pro-preview`
- `GEMINI_IMAGE_MODEL` for image rendering, default `gemini-3-pro-image`
- `OPENAI_API_KEY` for private medical knowledge embeddings
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY` for backend-only catalog publishing and private medical knowledge RPCs
- `ADMIN_EMAILS` for comma-separated catalog publisher emails
- `CORS_ORIGINS`
- `DEMO_AUTH_BYPASS`, default `true` in development, lets local Forge provider calls run without Supabase sign-in for demos. Production ignores this by default because `APP_ENV=production` keeps provider auth required.

## Private Medical Knowledge

The medical reference foundation is intentionally private: source chunks live in the non-public Supabase `medical` schema, browser clients do not receive raw chunks, and backend access uses service-role-only RPCs. Use `tools/ingest_medical_knowledge.py --dry-run` to inspect chunk counts before any upload. Actual ingestion requires `--confirm-send-to-openai` because PDF text must be sent to OpenAI to create embeddings.

## Notes For Future Work

- The forge page is still a large static HTML file with inline CSS and JS. Keep near-term edits targeted.
- `frontend/styles/app-shell.css` is the shared visual layer added during migration; prefer extending it before duplicating more page-local CSS.
- If the forge grows further, the next architecture step should be extracting shared frontend scripts and components without changing runtime behavior.

## Agent Sandboxes

For risky AI-assisted work, use a disposable git worktree instead of experimenting directly in the source-of-truth checkout:

```powershell
.\tools\New-MnemorizedAgentWorktree.ps1 -Name ui-polish
```

The sandbox workflow is documented in `docs/agent-sandbox-workflow.md`. Use one worktree per agent or experiment, keep `C:\Dev\Mnemorized` as the integration checkout on `main`, and remove sandboxes when finished:

By default, sandboxes are created under `C:\Dev\.agent-sandboxes\Mnemorized` so they do not clutter the project folder list.

```powershell
.\tools\Remove-MnemorizedAgentWorktree.ps1 -NameOrPath ui-polish -DeleteBranch
```

Optional validation helper:

```powershell
.\tools\Invoke-MnemorizedValidation.ps1 -Tests -SmokeServer
```

## Claude Code Shortcut

The intended desktop shortcut is `Mnemorized Claude Code`. It opens PowerShell 7 in `C:\Dev\Mnemorized` and runs:

```powershell
C:\Dev\Mnemorized\tools\Launch-Mnemorized-Claude.ps1
```

The repo-local agent guidance lives in `AGENTS.md`, `CLAUDE.md`, `.claude/`, and `.agents/`.
