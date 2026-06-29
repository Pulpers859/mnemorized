# Mnemorized Agent Instructions

Mnemorized is a static web frontend served by a FastAPI backend. Optimize for memory-palace generation quality, provider proxy safety, auth/persistence correctness, and careful edits to the large static forge page.

## Source Of Truth

- Active repo: `C:\Dev\Mnemorized`
- GitHub remote: `https://github.com/Pulpers859/mnemorized.git`
- Normal working branch: `main`
- Stale old copy: `C:\Users\Patrick's Computer\OneDrive - WV School of Osteopathic Medicine\Desktop\Mnemorized`

## Required Start

1. Confirm the repo path is `C:\Dev\Mnemorized`.
2. Run `git fetch --all --prune`.
3. Ensure the active branch is `main` tracking `origin/main`.
4. If clean, run `git pull --ff-only` before editing.
5. Identify the touched surface: backend, frontend page, shared style, deployment config, docs, or local tool.

## Branch And Git Rules

- Work on `main` for normal tasks.
- Do not create side branches or pull requests unless Patrick explicitly asks in the current conversation.
- Commit completed tracked changes directly to `main` and push to `origin/main` unless Patrick explicitly says not to.
- Never stage ignored local secrets, generated logs, archives, or local data.

## Product Rules

- Preserve the existing static/FastAPI architecture unless there is a specific product reason to introduce a build system.
- Treat `frontend/pages/forge.html` as fragile because it contains a large amount of inline UI and workflow logic.
- Prefer extending `frontend/styles/app-shell.css` before duplicating more page-local CSS.
- Keep real secrets in ignored `backend/.env`; keep `backend/.env.example` placeholder-only.
- Protect provider proxy behavior, auth context, quota enforcement, usage logging, and Supabase persistence paths from silent regressions.
- Be clear about what was validated locally and what still needs browser/provider-key testing.

## Skill-First Workflow

- At the start of a fresh session, use `.claude/skills/mnemorized-handoff/SKILL.md` or `.agents/skills/mnemorized-handoff/SKILL.md` unless the task is already deep in one known file.
- Use `mnemorized-context-compact` when resuming old work, preparing a handoff, or keeping a long review from ballooning.
- Use `mnemorized-parallel-audit` for broad reviews spanning backend, forge UI, library, auth, persistence, provider proxy, and deployment.
- Use focused skills for normal bug work:
  - `forge-static-ui-check`
  - `backend-auth-persistence-check`
  - `provider-proxy-quota-check`
- Prefer the smallest matching skill set; do not load every project doc by default.

## Validation

Run what is realistic for the change:

- Backend syntax: `python -m compileall backend`
- Server smoke: `python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
- Browser routes: `/`, `/forge`, `/library`, `/api/health`

Do not claim provider-generation validation unless local or hosted API keys were actually available and exercised.

