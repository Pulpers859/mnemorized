# Mnemorized — Running Handoff Doc

> **This is a rolling handoff.** It has two kinds of content:
> 1. **Standing reference** (Parts A–E): project orientation, glossary, key files,
>    how to run things, and the rules/lane. These stay stable — update only when
>    the project itself changes.
> 2. **Session log** (Part F): append-only. Each session adds a dated entry at the
>    TOP of the log. Never rewrite old entries; add a new one.
>
> **New agent, start here:** read Part A (orientation), Part D (rules — do not
> deviate), then the newest entry in Part F (where we left off). Skim Part B
> (glossary) and Part C (files) as needed. Then read the repo's `CLAUDE.md`,
> `AGENTS.md`, `docs/gemini-constitution.txt`, and `ANTIGRAVITY.md` — those are the
> authoritative source of truth; this doc is a fast on-ramp, not a replacement.

---

## PART A — What Mnemorized is (orientation)

Mnemorized turns a medical topic into a **memory-palace image** plus narration and
flashcards, for board study. A user types a topic into the **Forge**; a multi-stage
pipeline generates mnemonic anchors, gates them for medical accuracy, builds an
image prompt, and renders a plate.

**The pipeline (conceptual stages):**
1. **Stage 1 — Story / Scene Narrative.** Generates 8–10 **anchors** (each with a
   HOOK, VISUAL, ANCHOR fact, NARRATION). Validated by `validateStoryData`
   (structural gates: word caps, text-surface density, arrow glyphs, etc.). UI
   status id: `status-story`.
2. **Stage 2 — Medical Quality Gate.** Checks the script against retrieved medical
   evidence / an independent anchor contract. Needs sign-in + retrieval to fully
   run. UI status id: `status-quality`.
3. **Stage 3 — Image Prompt Builder.** Composes the constitution-guided
   illustration prompt(s) from the anchors (`buildImagePromptPair`). UI status id:
   `status-prompt`.
4. **Image render.** Either the **Gemini API** (`/api/generate-image`) OR
   **Antigravity** (desktop render lab). **Right now the loop uses Antigravity**
   because the Gemini image path is billing-blocked.
5. **Image audit.** Claude/Codex externally scores the rendered plate against the
   canonical rubric (≥96 to pass). AG never scores its own work.

**Providers:** Anthropic Claude Sonnet 4-6 (generation) with an Opus 4.8 **advisor**
in creative stages; Gemini (image + audit models); OpenAI embeddings; Supabase
(auth, persistence, quota); a private medical knowledge base (retrieval). Real keys
live in ignored `backend/.env`. Deploy is a single Render service (`render.yaml`).

---

## PART B — Glossary (terms you'll see everywhere)

- **Forge** — the main product page/workflow (`frontend/pages/forge.html` + the
  `frontend/scripts/forge-*.js` files). `forge.html` has NO inline JS.
- **Anchor** — one mnemonic unit. Has four fields:
  - **HOOK** — the memory device type: `sound-alike`, `look-alike`, `functional`,
    `contrast`, or `spatial`.
  - **VISUAL** — the drawing instruction. Target ≤24 words; >30 = warning; **>34 =
    fatal**. One object/character interaction + one location phrase.
  - **ANCHOR** — the clinical fact only (no mnemonic talk).
  - **NARRATION** — 2–3 spoken sentences.
- **Plate** — a focused render of 1–3 anchors in ONE coherent palace room. NOT a
  grid, tiled storyboard, or infographic. Grid layouts are a prompt failure.
- **Micro-repair** — `repairStoryVisualFormat`: a provider call that rewrites only
  VISUAL fields to fix Stage-1 format fatals. Now loops up to 3 passes.
- **Quality Gate / Medical Gate** — Stage 2. Grades the script; historically
  self-graded against its own anchors, now also checked against an independent
  **anchor contract**.
- **Lesson Blueprint** — archetype ontology + independent must-cover anchor
  contract, wired into Stage 1 and the quality gate.
- **Constitution** — `docs/gemini-constitution.txt`. Doctrine + numbered findings
  (#1…#27). Key LAWs: **#0** never fabricate; **#0.1** always drive the Forge; **#1**
  flowing prose not an annotated list; **#2** positive framing not negation.
- **Rubric** — `docs/image-scoring-rubric.md`. ONE canonical deterministic scorer:
  6 weighted categories (sum 100) minus per-defect deductions, then hard gates CAP
  the score. `OVERALL = min(RAW, caps)`. Pass = OVERALL ≥ 96 AND DECISION: PASS.
- **Metaphor library** — `docs/visual-metaphor-library.txt`. Sanctioned
  fact→object metaphors (banana=potassium, salt shaker=sodium, etc.).
- **Antigravity (AG)** — Google's desktop app, used here as a **render lab only**.
  Exposes a localhost `language_server.exe` + `agentapi` CLI. Port + CSRF token
  rotate every app restart, so every session begins with a discovery step.
- **agentapi bridge** — `tools/Invoke-AntigravityAgentApi.ps1`: auto-discovers the
  port/CSRF and drives AG. Path A (chat/image lane) is correct for image runs; the
  raw RPC / coding-cascade lane (Path B) is NOT for images (it drifts into repo
  work).
- **Troubleshooting Prompts/** — gitignored workspace for image runs. Per-plate
  convention: `01_image_prompt.txt`, `02_audit_prompt.txt`, `03_repair_rules.txt`
  in; `antigravity_iter1.png`, `antigravity_audit_iter1.md`, `antigravity_result.md`
  out.
- **Forge-first** — for a medical topic you MUST run the real Forge, not a
  hand-written prompt. Synthetic prompts are `renderer_experiment` only.
- **Replay / cassette** — dev-mode mechanism to replay cached provider responses
  (headers select record/replay).

---

## PART C — Files that matter most

- `CLAUDE.md` / `AGENTS.md` — workflow + risk priorities (read first).
- `frontend/pages/forge.html` — Forge UI (no inline JS).
- `frontend/scripts/forge-auth.js` — `validateStoryData` (Stage-1 structural gate:
  word caps + text-surface + arrows/speech bubbles), ~L293–345.
- `frontend/scripts/forge-pipeline.js` — the pipeline: `runPipeline`, story-attempt
  loop, `repairStoryVisualFormat` (~L1005), the iterative micro-repair loop
  (~L1533), `generateImages()` + the Antigravity render branch (~L708),
  `buildImagePromptPair`.
- `frontend/scripts/forge-image-audit.js` — in-app image audit + auto-retry loop.
- `frontend/scripts/forge-lesson-spec.js` — lesson blueprint / anchor contract.
- `backend/app/main.py` — FastAPI: `/api/generate-image` (Gemini proxy), `/forge`
  route, static mount, auth/quota/Supabase.
- `backend/app/config.py` — loads `backend/.env` (via `__file__`, cwd-independent).
- `docs/gemini-constitution.txt`, `docs/visual-metaphor-library.txt`,
  `docs/image-scoring-rubric.md`, `docs/visual-mnemonic-prompt-contract.md`.
- `ANTIGRAVITY.md` — authoritative AG workflow.
- `tools/run_forge_browser_stress.mjs` — real product-path harness (headless
  browser Forge run).
- `tools/Invoke-AntigravityAgentApi.ps1` — AG bridge helper.
- `render.yaml` — single Render service config.
- `.claude/skills/` and `.agents/skills/` — local skills; **edit both trees
  together** (they're duplicated).

**Highest-risk areas (from CLAUDE.md):** 1) provider proxy safety/errors; 2) auth,
Supabase persistence, quota; 3) Forge workflow regressions; 4) library save/load;
5) static frontend visual/state drift; 6) deployment config.

---

## PART D — Rules / lane the next agent must NOT break

- **LAW #0 — never fabricate.** Don't report intended output as observed; "I didn't
  check" is the honest answer. Verify on the real path before claiming it works.
- **LAW #0.1 — always drive the Forge.** NEVER hand-author medical
  anchors/prose/narration for an image run. Type the topic; let Stage 1 → medical
  gate → builder generate it. Hand-crafted prose is un-gated medical content.
- **Canonical image loop:** Forge → **Antigravity render (NEVER the Gemini API
  right now)** → external rubric audit by Claude/Codex → repair → repeat. AG never
  self-scores (it inflates).
- **Read `docs/gemini-constitution.txt` + `docs/visual-metaphor-library.txt`
  FIRST** for any hook/prompt work. Metaphor beats theme; pure visual metaphor is
  tier 1.
- **Mnemonics encode, never label.** The cover-the-text test: if you delete the
  label, the cue must still carry the fact. Exact numbers/doses are NEVER drawn —
  they go to NARRATION + flashcards.
- **One rubric only** — `docs/image-scoring-rubric.md`. Never invent a looser
  scorer. `OVERALL = min(RAW, caps)`; when torn, pick the lower score.
- **AG hard boundaries:** Antigravity only writes under `Troubleshooting Prompts/`;
  it never edits `backend/`, `frontend/`, `tools/`, `tests/`, `render.yaml`,
  `.env`, and never commits/pushes.
- **Repo discipline:** source of truth `C:\Dev\Mnemorized`, branch `main` →
  `origin/main`. Fetch at task start; `pull --ff-only` only on a clean tree. Commit
  + push completed tracked changes to `origin/main` unless Patrick says not to.
  Old OneDrive/Desktop copies are STALE unless Patrick asks to inspect them.
- **After every image/prompt run:** record structural findings (positive AND
  negative) into `docs/gemini-constitution.txt` and commit.
- **Cost protocol:** use **Sonnet subagents** for runs/audits/verification/broad
  audits (keep polling and big blobs out of the main Opus context). `/compact`
  after every commit and after every AG round-trip. `/clear` between topics. Keep
  Opus output short. Prefer fewer subagents doing more.
- **Patrick wants real debate**, not sycophancy. When you genuinely disagree with
  evidence, say so. Give a recommendation, not an option survey.

---

## PART E — How to run / verify (copy-paste)

Start the backend locally (loads ignored `backend/.env` automatically):
```bash
python -m uvicorn app.main:app --app-dir "C:/Dev/Mnemorized/backend" \
  --host 127.0.0.1 --port 8000
```
(If port 8000 already serves `/forge` with 200, an instance is already up — just
use it; a second launch will log "address already in use" and that's fine.)

Re-run any topic through the REAL product path (exercises the live gates):
```bash
node tools/run_forge_browser_stress.mjs --topic "<topic>" \
  --base-url http://127.0.0.1:8000 \
  --out-dir "C:/Dev/Mnemorized/Troubleshooting Prompts/<topic>_<date>"
```
It self-terminates when prompts are built (`prompt2Len > 1000`) or on a terminal
error. Read `05_run_meta.json` / `live_status.json` in the out-dir for the result.
Playwright ships in `local_archive/playwright-runner/` (gitignored); if missing,
`npm install playwright && npx playwright install chromium`.

Drive an Antigravity render (AG desktop app must already be running):
```powershell
.\tools\Invoke-AntigravityAgentApi.ps1 -Command NewConversation `
  -Title "<topic> Plate 1" `
  -PromptFile "C:\Dev\Mnemorized\Troubleshooting Prompts\<topic>\01_image_prompt.txt" `
  -PassPromptFileAsAtPath
```
Full AG operating detail is in `antigravity-operating-guide.md` (this desktop) and
authoritatively in repo `ANTIGRAVITY.md`. `-PassPromptFileAsAtPath` is required for
multi-line prompts or only the first line is sent.

Other useful tools: `tools/stress_visual_pipeline.py` (Python topic→image loop,
bypasses the browser gate), `tools/visual_qa_pack.py` (build a QA pack),
`tools/Invoke-MnemorizedValidation.ps1` (compile/test/smoke).

---

## PART F — Session log (append-only; newest first)

### 2026-07-09 — Stage-1 gate cluster fix + Antigravity toggle
**Done (all pushed to `origin/main`):**
- `5576f57` — Made the Stage-1 **text-surface gate precise** (`forge-auth.js`): was
  counting bare verbs ("shows"/"reads"/"showing") as drawn text → false rejects.
  Now counts text-bearing NOUNS + verbs only when they introduce a quoted label;
  quoted labels remain the true drawn-text fatal. Also added an **Antigravity
  render-target toggle** (`forge.html` `#image-target-antigravity` +
  `forge-pipeline.js`) that skips the Gemini API entirely and stages prompts for AG.
- `42a7b1c` — Made the visual **micro-repair iterative (up to 3 passes)** with a
  length-only escalation, so one dense anchor 1 word over the 34-word cap no longer
  aborts a whole 10-anchor scene. Threshold unchanged — fixed the failure MODE.
- `75829de` — Constitution **finding #27** documenting the above.

**Verified:** "status epilepticus" now clears Stage 1 on the real browser harness
(10 anchors, `prompt2Len=7415`, "image prompts ready"), where it previously aborted.

**Known risks / NOT verified:**
- Multi-pass repair loop only ran **1 pass** this run (generation variance) — the
  2nd/3rd escalation path is unexercised end-to-end.
- Antigravity toggle stops the Gemini call and stages prompts on
  `window.__mnemorizedAntigravityPrompts` + a custom event, but nothing consumes
  that automatically yet, and it wasn't clicked through in a live browser.
- `qualityStatus` returned "Check failed" — the medical **evidence gate** didn't
  finish in the harness (needs sign-in + retrieval). Unknown if environmental or a
  real gap. Separate from Stage 1.
- **No image has ever been rendered/scored for status epilepticus** — Stage 1 was
  the only blocker cleared; there is no plate or audit yet.

**Next highest-value step:** render status epilepticus through Antigravity and
audit it against `docs/image-scoring-rubric.md` — the Stage-1 unblock has no payoff
until a plate exists and is scored. Secondary: push a denser topic to actually
exercise the multi-pass repair; then chase the evidence-check gate.

---

### Template for future entries (copy this block, fill it in, place ABOVE)
```
### YYYY-MM-DD — <one-line title>
**Done (commits):** <hashes + one line each>
**Verified:** <what was proven, on what path>
**Known risks / NOT verified:** <honest gaps>
**Next highest-value step:** <the single most useful next action>
```
