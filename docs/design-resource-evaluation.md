# UI/UX Resource Evaluation

Date: 2026-06-29

## App Context

- Product: medical memory-palace generation, saving, and review.
- Primary users: physicians, medical students, and clinical learners who need fast, high-yield recall aids.
- Critical workflows: create a palace from source material, configure generation settings, review generated output, generate images, save/reopen saved palaces.
- Stack: static HTML/CSS/JS served by FastAPI.
- Current maturity: early product with useful backend foundations and a large static forge UI.
- Main design needs: clearer task hierarchy, calmer workspace density, stronger shared visual system, consistent account/library states, and safer maintenance boundaries.

## Decisions

| Resource | Decision | Rationale |
| --- | --- | --- |
| Builder.io Skills | Reference | Useful for visual plans/recaps and agent workflow ideas, but not needed as a permanent project install for this small static app. |
| UI UX Pro Max | Reference | Potentially useful as design intelligence during a dedicated redesign, but recommendations should be filtered through this app's medical workflow and static-web constraints. |
| 21st.dev | Reference | Useful for web component inspiration, not direct copy/paste because the app does not currently use React/Tailwind/shadcn. |
| UX Components | Reference | Useful for component behavior, states, accessibility, and interaction pattern checks. |
| UX Components Design Systems | Reference | Useful when formalizing tokens and component anatomy; do not overbuild a full design system yet. |
| Refero | Reference | Useful for real-product flow research, especially creation tools and libraries; extract principles instead of copying screens. |

## Combined Workflow

1. Define the exact screen or flow problem.
2. Inspect the live page and current code first.
3. Use Refero for comparable flow patterns only when a flow is being redesigned.
4. Use UX Components for state/accessibility requirements.
5. Use 21st.dev only for adaptable web component ideas.
6. Implement in the existing static/FastAPI architecture unless a build-system migration is explicitly planned.
7. Validate in browser at desktop and mobile widths.

## Current Implementation Choice

This migration added `frontend/styles/app-shell.css` as the first shared visual-system layer instead of introducing a component framework. That keeps the runtime stable while improving consistency across the landing, forge, and library pages.
