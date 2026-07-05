# Mnemorized Claude Workflow

Use `AGENTS.md` as the shared source for workflow and risk priorities.

Claude-specific assumptions:

- Source of truth: `C:\Dev\Mnemorized`
- Normal branch: `main` tracking `origin/main`
- Fetch at the start of a task; pull with `--ff-only` only when the tree is clean.
- Commit and push completed tracked changes to `origin/main` unless Patrick explicitly says not to.
- Old OneDrive/Desktop copies are stale unless Patrick explicitly asks to inspect them.
- Real local secrets live in ignored `backend/.env`.
- The main runtime surfaces are `backend/app/main.py`, `frontend/pages/*.html`, `frontend/scripts/*.js` (all forge behavior — forge.html has no inline JS), `frontend/styles/app-shell.css`, and `render.yaml`.

Highest-risk areas:

1. Provider proxy safety and error handling
2. Auth, Supabase persistence, and quota enforcement
3. Forge page workflow regressions
4. Library save/load behavior
5. Static frontend visual/state drift
6. Deployment configuration

Audit task pattern:

- For broad reviews spanning multiple risk areas, do NOT read every file into the main conversation.
- Spawn parallel Explore agents (model: sonnet) scoped to each risk area above. Each agent returns only: file path, line number, issue summary, severity.
- Main conversation applies fixes from findings using targeted Read (offset+limit), never full-file reads.
- Run `/compact` after each commit before starting the next phase.
- Run `/compact` after every AG round-trip (prompt → generate → audit cycle).
- Run `/clear` between topics — never carry dead iteration history into the next topic.
- Run test suite verification in a sonnet subagent, not inline.
- Follow the SESSION COST PROTOCOL in `docs/gemini-constitution.txt` for all iteration loops.

Claude-local workflow helpers:

- Use `@.claude/skills/mnemorized-handoff/SKILL.md` at the start of a fresh session unless the task is already deep in one known file.
- Use `@.claude/skills/mnemorized-context-compact/SKILL.md` for older work, mixed context, long logs, or handoff prep.
- Use `@.claude/skills/mnemorized-parallel-audit/SKILL.md` for broad reviews spanning multiple high-risk areas.
- For focused bugs, use `forge-static-ui-check`, `backend-auth-persistence-check`, and `provider-proxy-quota-check`.
- Before editing an unfamiliar surface, load the matching architecture map: `mnemorized-forge-map` (forge scripts, stage numbering, state model) or `mnemorized-backend-map` (backend invariants, quota mechanics, provider quirks).
- Use `mnemorized-validation` before commits, `mnemorized-deploy-check` for `render.yaml`/model rotation, and `antigravity-image-loop` for AG visual runs.
- Skills are duplicated in `.claude/skills/` and `.agents/skills/` — edit both trees together.
- Launching Claude through `tools/Launch-Mnemorized-Claude.ps1` opens directly in `C:\Dev\Mnemorized` and detects repo-local commands and skills.

