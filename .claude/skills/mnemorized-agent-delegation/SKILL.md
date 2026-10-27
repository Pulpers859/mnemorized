---
name: mnemorized-agent-delegation
description: Use for Mnemorized tasks that benefit from efficient main-agent/subagent delegation, including broad audits, cross-surface feature work, stress testing, UI/backend parallel review, or Patrick's requests to optimize token usage with agents.
---

# Mnemorized Agent Delegation

## Constitution

Main Codex is the architect, risk owner, and integrator. Subagents are bounded helpers for independent lanes. Do not delegate the immediate blocking task if the main agent needs its result before moving.

## Main Agent Owns

- Product and architecture decisions for the static/FastAPI app.
- Provider proxy safety, auth, Supabase persistence, quota, usage logging, billing, secrets, Render, and Supabase dashboard work.
- Final review, integration, validation, commits, and pushes to `main`.
- Any work touching `backend/.env` or production configuration.

## Good Delegation Lanes

- Explorer: inspect `backend/app/main.py` for one auth/quota/persistence risk.
- Explorer: inspect `frontend/pages/library.html` for catalog UI and responsive issues.
- Explorer: inspect service worker/cache/deployment behavior.
- Worker: update only tests in `tests/`.
- Worker: polish only `frontend/styles/app-shell.css`.
- Worker: patch one frontend script with no backend writes.

## Bad Delegation Lanes

- "Fix the app."
- "Make the UI premium."
- "Change auth and catalog and deployment together."
- Any task where multiple workers would edit `frontend/pages/forge.html` at the same time.

## Workflow

1. Rebuild Mnemorized context with `mnemorized-handoff`.
2. Identify the touched surface and immediate blocking task.
3. Keep the blocking task local.
4. Delegate only independent sidecar lanes with clear outputs.
5. Give each worker a disjoint write set and warn them not to revert others' edits.
6. Integrate results locally, then run realistic validation.

## Output Standard

Subagents should return concise findings with file paths, line references when possible, changed files if any, and validation performed. Main Codex should state what is evidence-backed versus inferred.

## Chapter Cue Workshops

Follow `docs/chapter-cue-workflow.md`. The paired pilot supports only provisional
lower-usage assistance for bounded source-head extraction, exact prior retrieval
and deterministic bookkeeping, not equivalent end-to-end cue authorship or net
savings. Keep cue selection, scope/collision/provenance adjudication and hold/reject
decisions with stronger authors; require non-author stronger review before main
integration. A smaller helper may flag exceptions, not decide semantic admission.

Resume saved freezes and source evidence. Freeze once, report concise exceptions,
repair concrete findings and recheck deltas rather than re-auditing unchanged
chapters/corpora. Specify FULL output versus a base-hash-keyed overlay explicitly;
materialize only declared operations and retain first artifacts. Scripts establish
structure/reference identity, not empirical or semantic success.

For future chapter runs, use the tracked `tools/chapter_cue_review_payloads.py`
helpers as documented in `docs/chapter-cue-workflow.md` (Audited Efficiency Tools):
narrow editorial warnings, exact semantic tables and lossless evidence cards.
Retain original-view fallback and independent all-row review. Local input-token
reductions are not measured quota/net savings; do not send both formats together.
