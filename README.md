# Mnemorized

Mnemorized is a web app for generating visual medical memory palaces, saving them to a Supabase-backed library, and routing AI provider calls through a FastAPI backend.

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
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `CORS_ORIGINS`

## Notes For Future Work

- The forge page is still a large static HTML file with inline CSS and JS. Keep near-term edits targeted.
- `frontend/styles/app-shell.css` is the shared visual layer added during migration; prefer extending it before duplicating more page-local CSS.
- If the forge grows further, the next architecture step should be extracting shared frontend scripts and components without changing runtime behavior.

## Claude Code Shortcut

The intended desktop shortcut is `Mnemorized Claude Code`. It opens PowerShell 7 in `C:\Dev\Mnemorized` and runs:

```powershell
C:\Dev\Mnemorized\tools\Launch-Mnemorized-Claude.ps1
```

The repo-local agent guidance lives in `AGENTS.md`, `CLAUDE.md`, `.claude/`, and `.agents/`.
