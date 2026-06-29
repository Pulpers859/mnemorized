---
name: mnemorized-parallel-audit
description: Break broad Mnemorized investigations into bounded lanes, gather evidence without context sprawl, and finish with one integrated judgment. Use for reviews spanning backend proxy/auth/persistence, forge UI, library behavior, static assets, and deployment.
---

# Mnemorized Parallel Audit

Use this skill when one careful pass is not enough, but a repo-wide sweep would waste context.

## Workflow

1. Confirm the source-of-truth repo is `C:\Dev\Mnemorized`.
2. Restate the real decision or risk in one sentence.
3. Split the work into 2-4 bounded lanes. Good lane types include:
   - provider proxy, quota, rate limit, and usage logging
   - auth, Supabase persistence, and library save/load
   - forge page UI/state/workflow behavior
   - shared app shell styling and responsive behavior
   - deployment config and static asset routing
4. For each lane, define:
   - the narrow question
   - exact files or artifacts to inspect
   - evidence needed
   - stop condition
5. After each lane or wave, write a compact recap.
6. Synthesize only after evidence passes are done.

## Review Priority

Findings should be ordered by:

1. secrets exposure or unsafe provider proxy behavior
2. auth, quota, or persistence bugs
3. broken forge generation or save workflow
4. library load/reopen regressions
5. deployment/runtime route failures
6. maintainability issues likely to compound

