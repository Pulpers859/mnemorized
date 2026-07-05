---
description: Run a targeted pre-ship quality pass for a Mnemorized feature, file, or surface.
argument-hint: [feature-or-path]
---

Run a lean pre-ship review for `$ARGUMENTS`.

Workflow:

1. Identify whether the work is backend, forge UI, library UI, shared styling, deployment, or docs.
2. Use only the relevant project skills:
   - `forge-static-ui-check`
   - `backend-auth-persistence-check`
   - `provider-proxy-quota-check`
   - `mnemorized-deploy-check` (if `render.yaml` or env wiring changed)
3. Review for:
   - provider proxy regressions
   - auth or persistence failures
   - quota or usage-logging drift
   - broken forge/library flows
   - secrets or deployment config mistakes
4. Run `powershell -File tools/Invoke-MnemorizedValidation.ps1 -Tests -SmokeServer` (or the relevant subset) and report which layers ran.
5. Return findings first, ordered by severity, with exact file references.
6. Keep the summary brief.

