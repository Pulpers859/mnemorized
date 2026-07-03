# Antigravity Visual QA Workflow For Mnemorized

This file defines the safe default workflow for using Google Antigravity with Mnemorized.

Antigravity's primary role in this repo is **visual QA lab**, not app integrator. Use it for image generation, image-audit loops, prompt repair experiments, and visual artifact reports. Codex or Claude should integrate durable findings into source code, tests, and commits unless Patrick explicitly asks Antigravity to make code changes.

## Source Of Truth

- Active repo: `C:\Dev\Mnemorized`
- General repo rules: `AGENTS.md`
- Medical visual prompt contract: `docs/visual-mnemonic-prompt-contract.md`
- Visual experiment workspace: `Troubleshooting Prompts/`

Do not use the stale OneDrive/Desktop app copy for app work.

## Default Role

Use Antigravity for:

- generating trial images from Mnemorized prompt packs
- auditing generated images against the anchor table/rubric
- repairing or regenerating visual prompts until they pass
- saving image/audit artifacts in the relevant troubleshooting folder
- writing concise findings that Codex/Claude can fold back into the app

Do not use Antigravity by default for:

- backend/provider proxy changes
- Supabase/auth/quota/persistence changes
- Render/env/secrets work
- commits or pushes
- broad refactors
- editing `frontend/pages/forge.html`

## Hard Boundaries

- Do not modify `backend/`, `frontend/`, `tools/`, `tests/`, `render.yaml`, `.env`, or secret/config files unless Patrick explicitly asks in the current prompt.
- Do not call Mnemorized backend provider endpoints for image generation unless Patrick explicitly approves API spend.
- Do not read unrelated private folders.
- Do not use patient-identifying information.
- Do not copy proprietary Sketchy/Pixorize scenes, characters, symbols, layouts, or fact-to-symbol mappings. Reusable design principles are allowed; copying visual vocabulary is not.
- Save generated images and audit notes only under `Troubleshooting Prompts/` unless instructed otherwise.

## Visual QA Passing Standard

Each image plate must pass:

- `OVERALL_SCORE >= 96`
- `DECISION: PASS`

Use the audit format from the plate's `02_audit_prompt.txt` or generated QA pack. Do not invent a looser scoring system.

## Plate Folder Convention

For a manual plate folder such as:

```text
Troubleshooting Prompts\...\plate_N\manual_retry
```

Expected inputs:

- `01_image_prompt.txt`: paste into image generation.
- `02_audit_prompt.txt`: use to audit the generated image.
- `03_repair_rules.txt`: use only after an audit returns `REPAIR` or `REGENERATE`.

Expected outputs:

- `antigravity_iter1.png`
- `antigravity_audit_iter1.md`
- `antigravity_iter2_repair.png` or `antigravity_iter2_regen.png` when needed
- `antigravity_result.md` when the plate passes
- `antigravity_blocked.md` if the plate cannot pass after bounded attempts

## Standard Loop

1. Read `AGENTS.md`, this file, and `docs/visual-mnemonic-prompt-contract.md`.
2. Work only in the requested topic/plate folder under `Troubleshooting Prompts/`.
3. Read `01_image_prompt.txt`.
4. Generate an image from that prompt using Antigravity's built-in image generator.
5. Save the image as `antigravity_iter1.png`.
6. Read `02_audit_prompt.txt`.
7. Audit the generated image against that rubric and the image itself.
8. Save the audit as `antigravity_audit_iter1.md`.
9. If the score is `>=96` and decision is `PASS`, write `antigravity_result.md` and stop that plate.
10. If the audit says `REPAIR`, read `03_repair_rules.txt`, repair the current image, save the next image, and re-audit.
11. If the audit says `REGENERATE`, regenerate from `01_image_prompt.txt` plus the audit's `REGENERATION_PROMPT_CHANGE`, save the next image, and re-audit.
12. Stop after 5 total attempts per plate. If still failing, write `antigravity_blocked.md` with the failure pattern and recommended prompt-level fix.

## What To Report Back

For each completed topic or plate set, write a summary markdown file in the topic troubleshooting folder with:

- plate status
- best score per plate
- final image filenames
- final audit filenames
- prompt repair lessons
- systemic weaknesses that should be folded back into `docs/visual-mnemonic-prompt-contract.md` or the Forge pipeline

Keep findings concise and evidence-backed. Do not claim an image passed unless the saved audit says `OVERALL_SCORE >= 96` and `DECISION: PASS`.

## Starter Prompt For Antigravity

Use this as the first prompt when starting a Mnemorized visual QA task:

```text
Read `AGENTS.md`, `ANTIGRAVITY.md`, and `docs/visual-mnemonic-prompt-contract.md`.

You are the Mnemorized Visual QA Lab. Work in `C:\Dev\Mnemorized`.

Your job is to generate and audit visual mnemonic images from existing prompt packs, not to modify source code.

Use only the requested folder under `Troubleshooting Prompts/`. Do not edit `backend/`, `frontend/`, `tools/`, `tests/`, `.env`, or deployment config. Do not commit or push. Do not call the Mnemorized backend/provider API for image generation unless I explicitly approve API spend.

For each requested plate folder:
1. Read `01_image_prompt.txt`.
2. Generate an image with Antigravity's built-in image generator.
3. Save it as `antigravity_iter1.png` in the same folder.
4. Read `02_audit_prompt.txt`.
5. Audit the generated image against the rubric.
6. Save the audit as `antigravity_audit_iter1.md`.
7. Passing means `OVERALL_SCORE >= 96` and `DECISION: PASS`.
8. If `REPAIR`, use `03_repair_rules.txt` plus the audit's `REPAIR_PROMPT`, save the repaired image, and re-audit.
9. If `REGENERATE`, use `01_image_prompt.txt` plus the audit's `REGENERATION_PROMPT_CHANGE`, save the regenerated image, and re-audit.
10. Stop after 5 total attempts per plate. If still failing, write `antigravity_blocked.md` explaining the exact failure pattern and recommended prompt-level fix.

When done, write a concise summary markdown file in the topic troubleshooting folder with scores, final image filenames, audit filenames, and any systemic prompt lessons Codex/Claude should fold back into the app.

Requested folder(s):
[PASTE THE TOPIC OR PLATE FOLDER PATHS HERE]
```

