---
name: forge-static-ui-check
description: Review Mnemorized static frontend changes, especially the large forge page, for UI state, inline JS/CSS, route behavior, shared shell consistency, and responsive regressions.
---

# Forge Static UI Check

Use this when work touches `frontend/pages/*.html`, `frontend/styles/app-shell.css`, `frontend/manifest.json`, `frontend/sw.js`, or static assets.

## Workflow

1. Identify the page or flow: landing, forge, library, saved palace review, account state, image generation, or install/PWA behavior.
2. Inspect the smallest relevant HTML, CSS, and inline JS block.
3. Check:
   - primary action remains obvious
   - loading, error, empty, disabled, and saved states are visible
   - provider/auth failures do not look like success
   - shared app-shell CSS is reused before adding page-local styling
   - mobile width does not hide controls or critical output
4. If the change touches forge generation, trace request payload construction and response rendering.
5. Validate in browser when practical; otherwise state that browser behavior is correct-by-inspection only.

## Avoid

- broad page rewrites for a small bug
- introducing a build system unless explicitly planned
- duplicating shared visual rules already covered by `frontend/styles/app-shell.css`

