---
description: Trace a Mnemorized bug through the smallest relevant backend or frontend path.
argument-hint: [bug-report]
---

Debug `$ARGUMENTS` with a narrow workflow.

Process:

1. Restate the bug in product terms.
2. Identify the likely failure mode:
   - provider proxy or generation request
   - auth, account, quota, or Supabase persistence
   - forge page UI/state
   - library save/load
   - deployment/static asset routing
3. Use the matching project skill instead of doing a broad repo tour.
4. Trace the request or data path end to end.
5. Return:
   - most likely fault location
   - why it causes the reported behavior
   - smallest safe fix
   - what still needs runtime verification

