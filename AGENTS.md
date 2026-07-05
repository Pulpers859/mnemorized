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
- Intentional demo behavior: local/development Forge provider calls bypass Supabase sign-in by default via `DEMO_AUTH_BYPASS=true` so Patrick can demo generation without auth friction. Do not remove this as a bug. Production must still require auth unless Patrick explicitly reopens the live-publish auth work.
- Protect provider proxy behavior, auth context, quota enforcement, usage logging, and Supabase persistence paths from silent regressions.
- Treat `docs/visual-mnemonic-prompt-contract.md` as the source of truth for medical visual mnemonic prompt quality and the boundary against copying proprietary visual mnemonic products.
- Treat `ANTIGRAVITY.md` as the source of truth for Google Antigravity visual QA/image-generation experiments. Antigravity should stay in the visual lab lane unless Patrick explicitly asks it to edit app source.
- For Google Antigravity image-generation loops, use the `agentapi.bat new-conversation` lane documented in `ANTIGRAVITY.md` when automation is available. Do not use raw `StartCascade` / `SendUserCascadeMessage` RPC for image runs; that routes to Antigravity's coding-agent lane and wastes time on repo inspection.
- For prompt/image troubleshooting loops, save the full run packet under `Troubleshooting Prompts/`: source prompt, anchor/narration table, repair prompts, generated images/screenshots, audit rubric, scores, and caveats. Do not claim a clean `>=96` pass unless the saved audit/rubric supports it.
- Treat `docs/gemini-constitution.txt` as mandatory for image-generation prompt repair. If a fallback path or Gemini web run did not fully use the Constitution, say so explicitly in the saved run notes and final response.
- Be clear about what was validated locally and what still needs browser/provider-key testing.

## Skill-First Workflow

- At the start of a fresh session, use `.claude/skills/mnemorized-handoff/SKILL.md` or `.agents/skills/mnemorized-handoff/SKILL.md` unless the task is already deep in one known file.
- Use `.agents/skills/mnemorized-agent-delegation/SKILL.md` when Patrick asks for efficient agent usage, broad audits, stress testing, cross-surface feature work, or parallel review.
- Use `mnemorized-context-compact` when resuming old work, preparing a handoff, or keeping a long review from ballooning.
- Use `mnemorized-parallel-audit` for broad reviews spanning backend, forge UI, library, auth, persistence, provider proxy, and deployment.
- Use focused skills for normal bug work:
  - `forge-static-ui-check`
  - `backend-auth-persistence-check`
  - `provider-proxy-quota-check`
- Prefer the smallest matching skill set; do not load every project doc by default.

## Delegation Constitution

- Main Codex acts as architect, risk owner, and integrator.
- Keep provider proxy safety, auth, Supabase persistence, quota, usage logging, billing, secrets, Render, Supabase dashboard work, commits, and pushes under main-agent control.
- Use explorer subagents for bounded read-only questions with evidence-backed findings.
- Use worker subagents only for disjoint write scopes with explicit file/module ownership.
- Do not delegate the immediate blocking task when the main agent needs that result before moving.
- Avoid overlapping edits to `frontend/pages/forge.html`; it is fragile and should have one owner at a time.
- Require subagents to report changed files, validation run, and any uncertainty.
- For risky, creative, or parallel agent work, prefer one disposable git worktree per agent or experiment. Use `docs/agent-sandbox-workflow.md` and `tools/New-MnemorizedAgentWorktree.ps1`.
- Keep `C:\Dev\Mnemorized` as the integration checkout on `main`; use Docker or the Dev Container only when dependency/process isolation is worth it.

## Validation

Run what is realistic for the change:

- Backend syntax: `python -m compileall backend`
- Server smoke: `python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
- Browser routes: `/`, `/forge`, `/library`, `/api/health`

Do not claim provider-generation validation unless local or hosted API keys were actually available and exercised.
