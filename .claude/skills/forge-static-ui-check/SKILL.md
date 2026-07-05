---
name: forge-static-ui-check
description: Review Mnemorized static frontend changes — pages, the forge script files in frontend/scripts/, shared shell CSS — for UI state, route behavior, id-hook coupling, cache busting, and responsive regressions.
---

# Forge Static UI Check

Use this when work touches `frontend/pages/*.html`, `frontend/scripts/*.js`, `frontend/styles/app-shell.css`, `frontend/manifest.json`, `frontend/sw.js`, or static assets.

Forge behavior lives in `frontend/scripts/forge-*.js`, not in forge.html (which carries inline CSS and id hooks only). For forge architecture, stage numbering, and fragility hotspots, load `mnemorized-forge-map` first.

## Workflow

1. Identify the page or flow: landing, forge, library, saved palace review, account state, image generation, or install/PWA behavior.
2. Inspect the smallest relevant HTML, CSS, or script region. When changing HTML, grep any touched `id` across `frontend/scripts/` — JS couples to ids with no compile-time check.
3. Check:
   - primary action remains obvious
   - loading, error, empty, disabled, and saved states are visible
   - provider/auth failures do not look like success
   - shared app-shell CSS is reused before adding page-local styling
   - mobile width does not hide controls or critical output (shared shell breaks at 760px; forge-local CSS at 600px — test both)
   - changed `forge-*.js` files get a bumped `?v=` query on their script tag
   - service worker cache name in `frontend/sw.js` is bumped when cache shape changes (SW registers only on landing and library)
4. If the change touches forge generation, trace request payload construction and response rendering.
5. Run `python -m pytest tests` even for frontend-only changes — `tests/test_provider_and_static_boundaries.py` asserts against the static HTML.
6. Validate in browser when practical; otherwise state that browser behavior is correct-by-inspection only.

## Avoid

- broad page rewrites for a small bug
- introducing a build system unless explicitly planned
- duplicating shared visual rules already covered by `frontend/styles/app-shell.css`

