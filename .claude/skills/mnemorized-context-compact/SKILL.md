---
name: mnemorized-context-compact
description: Keep Claude Code context lean in Mnemorized by rebuilding only the project state needed for the current task, choosing the right local skill, and producing compact handoffs.
---

# Mnemorized Context Compact

Use this skill when the session needs enough context to be safe without rereading the whole repository.

## Workflow

1. Start with the current user request and root `AGENTS.md`.
2. Use `mnemorized-handoff` for fresh repo orientation.
3. Choose one deeper skill first:
   - `forge-static-ui-check` for `frontend/pages/*.html`, inline JS/CSS, app shell styling, and route UX
   - `backend-auth-persistence-check` for auth, Supabase, library persistence, saved palaces, and account state
   - `provider-proxy-quota-check` for provider calls, quotas, rate limits, usage logging, and API errors
   - `mnemorized-parallel-audit` for broad reviews across multiple risk areas
4. Open only files directly needed for the task.
5. Before editing or ending, summarize state in 5-8 bullets:
   - what was checked
   - what was found
   - what is evidence-backed
   - what is inferred
   - what remains unverified
   - next best move

## Rules

- Do not load all docs or skills by default.
- Prefer targeted searches, line-level reads, and compact recaps.
- Keep provider safety, persistence correctness, and forge workflow integrity ahead of process ceremony.

