# Project Handoff

## Project Identity

- Project name: `Mnemorized`
- Project type: static web frontend plus FastAPI backend
- Source-of-truth repo path: `C:\Dev\Mnemorized`
- Stale/old copy to ignore: `C:\Users\Patrick's Computer\OneDrive - WV School of Osteopathic Medicine\Desktop\Mnemorized`
- GitHub remote: `https://github.com/Pulpers859/mnemorized.git`
- Current stable/working branch: `main`
- Branch note: normal work should stay on `main` unless explicitly requested otherwise.

## Live Runtime

- Backend app: `backend/app/main.py`
- Frontend pages:
  - `frontend/pages/landing.html`
  - `frontend/pages/forge.html`
  - `frontend/pages/library.html`
- Shared visual shell: `frontend/styles/app-shell.css`
- PWA files:
  - `frontend/manifest.json`
  - `frontend/sw.js`
- Runtime image asset: `frontend/assets/profile-pic.png`
- Deploy config: `render.yaml`

## Support Material

- Standalone local mapper: `tools/forge-anchor-mapper.html`
- Backend architecture notes: `docs/backend/auth-persistence-foundation.md`
- UI/UX resource decision memo: `docs/design-resource-evaluation.md`
- Local ignored material retained inside the repo folder but outside Git:
  - `C:\Dev\Mnemorized\local_archive\2026-06-29\projects`
  - `C:\Dev\Mnemorized\local_archive\2026-06-29\Profile_pic.afdesign`

## Agent Workflow

- Work only in `C:\Dev\Mnemorized` unless explicitly asked to inspect the old copy.
- Fetch before normal work. If the tree is clean and tracking is intact, pull with `--ff-only`.
- Keep real secrets in ignored `backend/.env`; keep examples placeholder-only.
- Preserve the existing static/FastAPI architecture until there is a specific reason to introduce a build system.
- Treat `frontend/pages/forge.html` as fragile because it contains a large amount of inline UI and workflow logic.
- After edits, run at least:
  - `python -m compileall backend`
  - `python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
  - browser checks for `/`, `/forge`, `/library`, `/api/health`

## PowerShell / Agent Standard

- Do not globally pin every PowerShell session to this project.
- A dedicated desktop shortcut should exist:
  - `Mnemorized Claude Code`
- That shortcut should open directly in `C:\Dev\Mnemorized`.
- The shortcut should call `tools/Launch-Mnemorized-Claude.ps1` through PowerShell 7 when available.
- Repo-local agent guidance lives in `AGENTS.md`, `CLAUDE.md`, `.claude/`, and `.agents/`.
- Use `mnemorized-handoff` for fresh orientation, `mnemorized-context-compact` for resumed or long work, and `mnemorized-parallel-audit` for broad investigations.
- Use `mnemorized-agent-delegation` when Patrick wants efficient main-agent/subagent coordination.
- Use focused skills for normal bug work: `forge-static-ui-check`, `backend-auth-persistence-check`, and `provider-proxy-quota-check`.

## Delegation Preference

Patrick prefers main Codex to carry high-judgment architecture, risk, integration, secrets, production, and commit/push work while delegating bounded independent lanes to explorer or worker subagents. Explorers should answer specific read-only questions. Workers should own disjoint file/module scopes and must not revert other edits.

## Known Constraints

- The app can load without provider keys, but generation endpoints require local or hosted secrets.
- Supabase auth/library features are enabled only when Supabase config exists.
- The current working branch is `main`, matching the preferred workstation default.
