---
name: mnemorized-handoff
description: Orient Claude Code to the real Mnemorized repo, source-of-truth paths, branch rules, runtime surfaces, stale-copy risk, and high-risk workflows. Use at the start of a Mnemorized task, when preparing a handoff, or when rebuilding project context before editing.
---

# Mnemorized Handoff

Use this skill to rebuild the minimum correct context before coding, reviewing, or handing work to another session.

## Workflow

1. Confirm the source-of-truth repo is `C:\Dev\Mnemorized`.
2. Confirm the active branch is `main`, tracking `origin/main`.
3. Run `git fetch --all --prune`; if the tree is clean, run `git pull --ff-only`.
4. Confirm the main runtime surfaces:
   - backend app: `backend/app/main.py` (config in `backend/app/config.py`, auth in `backend/app/auth.py`)
   - frontend pages: `frontend/pages/landing.html`, `frontend/pages/forge.html`, `frontend/pages/library.html`, `frontend/pages/admin.html`
   - forge behavior: `frontend/scripts/forge-*.js` and `frontend/scripts/palace-api.js` (forge.html itself has no inline JS)
   - shared visual shell: `frontend/styles/app-shell.css`
   - deploy config: `render.yaml`
5. Read the smallest relevant instruction file:
   - `AGENTS.md` for shared operating rules
   - `CLAUDE.md` for Claude-specific assumptions
6. Explicitly call out stale copies if they appear in the task context.
7. Identify the touched surface before editing: backend, forge UI, library UI, shared style, deployment, docs, or local tool.

## Product Risk Order

1. Provider proxy safety and error handling
2. Auth, quota, usage logging, and Supabase persistence
3. Forge page workflow correctness
4. Library save/load behavior
5. Static frontend visual/state drift
6. Deployment configuration

## Rules

- Work from `C:\Dev\Mnemorized`.
- Keep normal work on `main`; do not create side branches or PRs unless Patrick explicitly asks.
- Treat `backend/.env`, logs, local archives, and generated data as local-only.
- Preserve the static/FastAPI architecture unless a task explicitly justifies changing it.
- Do not claim provider-generation validation unless real keys were available and exercised.
- Skills live in BOTH `.claude/skills/` and `.agents/skills/` — when editing a skill, apply the same change to both trees.
- Validate with `tools/Invoke-MnemorizedValidation.ps1 -Tests -SmokeServer` (see `mnemorized-validation`); CI runs compileall + pytest on push/PR but does not gate deploys.

