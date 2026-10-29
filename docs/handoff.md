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
- **Chapter cue allocation:** follow `docs/chapter-cue-workflow.md`; bounded
  extraction/retrieval/mechanical checks may use smaller helpers, but stronger
  authors and non-author reviewers own cue/scope/provenance/hold judgment. This
  chapter-specific tested split takes precedence over generic model-role examples.
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

### 2026-10-28 - Council roadmap and first-attempt infrastructure

Patrick requested a council and substantial execution, not another planning-only
answer. Roadmap: docs/one-shot-roadmap.md. Two bounded AI agents (Raman evaluation,
Galileo compiler/test worker), main retained provider/budget/Git ownership. No
chapter mining, paid calls or AG renders. Chapters101-105 remain deferred.

Implemented opt-in immutable first-attempt profile: four ordered Sonnet calls,
eight-unit/source prerequisites, no retries/micro/clinical/visual repairs or expert
escalation, terminal failures and export metadata. Candidate's only story-prompt
difference is removing the body-system setting metaphor row. Normal Forge default
list/repair behavior unchanged. Alternate Gemini director/API image lane blocked
for experimental profiles; use frozen AG handoff. Browser runner supports arm/ID.

Implemented SQLite reservation REHEARSAL under optional RESEARCH_BUDGET_PATH:
final source/Constitution/tool-aware count request, immutable reservations,
restart/concurrency/ceilings, early stage/profile/replay rejection, no live embeddings
or alternate provider lanes. ALWAYS blocks billable Messages dispatch; there is NO
live switch or hard-dollar-cap claim. Docs: research-admission-rehearsal.md.
Optional cohort first_attempt metadata makes existing ledger registration require
the matching arm/topic/four-call receipt and zero pre-render repairs.

Independent review caught embedding/replay/type-handling gaps; main fixed and
reviewer delta found no remaining material safety issue (static review only).
Worker's adversarial tests caught beta-header/failure-state gaps; fixed54/54pass.
Budget35/35pass. Packet: Troubleshooting Prompts/roadmap_2026-10-28/ includes council
decisions, prospective audit protocol and desktop/mobile safety screenshots.

Remaining: defensible LIVE financial admission first, then actual blinded rubric
calibration, novelty draw, shared pairing manifest/two frozen ledgers and six-image
trial. Existing$6TOTAL/six-render limits unchanged. Do not bypass409, rotate a ledger,
resume chapter mining or claim software tests establish image reliability.

Closeout validation:1274passed/2skipped/165subtests; compileall and JS syntax passed,
four HTTP200route smokes passed, desktop1440/mobile390browser safety checks passed,
diff check clean. First full regression's two stale exact-string assertions were
updated for the intentional conditional code, not image criteria relaxed. No
live provider/full medical-generation/image/recall validation. Both agents closed.
Known malformed local Codex checkpoint ref still prevents fetch; no retry/delete.
Remote SHA verified directly before normal non-force push, then verify HEAD/SHA,
0/0 and previous remote ancestry. Never claim CIpass without checking actual run.

### 2026-10-28 - Stop blanket mining; implement Forge-gap cue workflow

Patrick approved ending exhaustive library expansion in favor of real Forge gaps.
Current default is now in chapter-cue-workflow.md, AGENTS.md and both delegation
skills. Generic continue does not resume101-105. Source inventories and101author
draft preserved/deferred, no independent cue approval/integration; both agents closed.
Catalog76, holds1133/935 and canonical next101 unchanged.

Extended existing chapter_cue_prior_matches.py with repeated --term lookup, exact
cue/scope content IDs, separate selected/held/blocked groups and truncation counts.
No synthetic query banks, auto-admission, medical inference or production injection.
Tests cover grouping, provenance, missing scope, restrictions, limits and CLI.
Retrospective real serotonin export/feedback lookup is in
Troubleshooting Prompts/forge_cue_gap_reset_2026-10-28/. Existing candidates may
help cue identity, not physical placement; no new cue selection or image score.
No paid calls. Original $6/six-render plan remains subject to its enforceable
final-request spending gate, not supplied by these offline tools.

Validation:1184passed/2skipped/149subtests; backend compileall and four HTTP200
route smokes passed. Catalog validates76entries; hold register current; mirrored
skills identical; diff check clean. Main code review and regression tests, not a
new independent semantic/pixel audit. No browser/provider/recall validation.
Git fetch remains blocked by the previously diagnosed malformed local Codex
checkpoint ref; no retry/delete. Authenticated remote SHA checked directly before
push; normal push and post-push SHA/ancestry checks are the synchronization route.

### 2026-10-28 - Batch101-105 source freezes; creative work in progress
**Source done, cue review NOT done:** All five purchased OBGYN inventories source
reviewed/prepared before creativity:1,266terms/1,474keyword mappings.101372/425,
102209/268,103192/226,104265/302,105228/253.101two bounded source findings and
102one heading repaired/delta-closed;103-105finding-free. BlankPDF62excluded;
actual105ends61. No clinical normalization/exhaustive coverage/recall claim.
**Active:** Same author Ptolemy01a1802d-b15a-7742-8028-35343e4f4160 creative101;
same independent reviewer Franklin01a1802e-e725-7513-a7a7-85117b08a3a9 waiting
for authored101bank. No newcohort/efficiencyexperiment/paidproviders/renders.
**Resume:**Troubleshooting Prompts/tintinalli_chapter_cues_2026-10-28/batch101-105/
resume-checkpoint.md and source-review.md; report docs/chapter-101-105-cue-workshop.md.
Ledger stillnext101; do not skip or regenerate source/prior preparation over
choices. Preserve1,133older active holds. Stop105; next106EmergencyCareofChildren.
No101-105bank integrated or final validation/commit yet; prior5e67224is synced.

### 2026-10-28 - Chapters96-100 independently reviewed and integrated
**Done:** One strong author(Ptolemy) and one non-author strong reviewer(Franklin),
resumed in the same contexts after usage pause. All five source inventories and
ALL781cue/scope/prior/target-note rows independently reviewed; main corroborated
material findings and integrated hash-bound final banks.901keyword mappings:
35different-bridge occurrences,37variants,708repeats,1hold. Not unique library
growth or measured recall/render quality; canonical catalog76unchanged.
**Review:**96four findings/five changed rows;97two/two;98two/two;99one/one;
100no concrete bank findings. Final evidence-note consistency cleared; first
draft/first-valid/first-MAIN/author-final/repair histories preserved. Source repairs
were two97emphasis labels, one98limits phrase and four100omitted lexical heads.
No new source pass after bounded repairs. Full-width table98onPDF16 separated
from99; purchased OBGYN hash/offset606/actual transitions independently verified.
**Holds:**All1,132older core active holds and older resolutions preserved;
register1,133occurrences/935terms. Only new active96Ginseng. Yaz reselects its
same first local held jazz-sax attempt, explicit history/resolution, not new yield
or resolution of any external hold. Older holds stay on the separate revisit list.
**Validation:**273focused checks passed; full1,172passed2skipped/149subtests;
backend compile and all4HTTP200route smokes passed, temporary server terminated.
No paid provider calls, Anthropic calls, AI renders or production cue admission.
Codex work used account usage; no efficiency experiment or savings claim.
**Next:**101 Emergency Delivery, not started; fixed batch stops100. Report:
docs/chapter-96-100-cue-workshop.md. Raw packet and final Git closeout:
Troubleshooting Prompts/tintinalli_chapter_cues_2026-10-27/batch96-100/.
Both agents finished and closed; no unfinished96-100lane. Main tracks origin/main.
Known malformed local Codex checkpoint still blocks fetch; no retry/ref deletion.
Authenticated GitHub branch and local HEAD matched3b7fe4ab before this commit;
final push/remote proof is recorded in the packet closeout, not inferred from tests.

### 2026-10-27 - Chapters91-95integrated; real workflow observed
**Done:** Completed saved93repair and94/95authoring with one bounded stronger
author(Newton) and one non-author stronger reviewer(Herschel). Main corroborated
findings and integrated all five reviewed hashes.888terms/1,044keyword mappings:
51different-bridge occurrences,46variants,789repeats,2holds; not unique growth.
All candidates untested/nonproduction. Source/initial/first-valid/first-MAIN and
repair artifacts retained. Chapter96Abnormal Uterine Bleeding is next, not started.
**Review:**93two-row delta closed;94three classification findings closed,160rows
unchanged;95one hold-rationale finding closed,140unchanged.95reselects the exact
supper-setting attempt as reconsidered/unchanged rather than fresh invention.
Only that local first-draft hold resolved. All1,130older core holds preserved;
newactive91Schistosomiasis and94Ephedrine. Register1,132occurrences/934terms.
**Efficiency:** Both new compact views failed the earlier5%hurdle:94=4.62%,
95=2.16%; originals dispatched, no format savings credited. Zero configured
editorial warnings, but semantic/classification review still required repairs.
Agent recovery reads/preparation cost remains. No metered quota/net-saving claim,
no paid providers/images, no new council or source restart. Five-report prototype
not used for smaller assignments. Observation log and independent audit are under
Troubleshooting Prompts/tintinalli_chapter_cues_2026-10-26/batch91-95/.
**Validation:**375focused checks passed; full1,156passed2skipped/149subtests;
backend compile and all4HTTP200route smokes passed. No clinical/render/recall or
live-generation validation. Report:docs/chapter-91-95-sparse-workshop.md. Existing
chapter progress edits reconciled; materializer code/source/prior freezes unchanged.
**Git:**Pre-commit main/origin/authenticatedremote matched6272dfb; normal push
and post-push remote verification recorded in the task closeout. Known malformed
local Codex ref still blocks fetch; no ref deletion or credential retry.

### 2026-10-26 - Persist audited efficiency workflow; reject source-range trial
**Done:** Promoted previously audited semantic-table, retrieval-card and narrow
editorial-warning helpers into stdlib-only `tools/chapter_cue_review_payloads.py`
with a read-only UTF-8 CLI and53focusedtests. Standing chapter workflow, AGENTS
and both mirrored delegation skills now direct future runs to the tracked tool.
Raw provenance remains under Troubleshooting Prompts/token_efficiency_council_2026-10-26.
No provider calls, image renders or new medical-cue authoring.
**New trial:** Ordered source-exclusion span ranges preserve original view text
on all five saved chapters and pass5focusedtests, but17,501to15,772local input
tokens is9.88%, below the frozen15%gate. Rejected; no source-view promotion.
Prior retrieval-card22.48% and semantic-view9.58%/5.43%measurements remain
surface-specific local tokenizer proxies, not total quota or net-cost savings.
**Current chapter state:**91/92independently closed, not integrated;93saved
two-row repair awaits materialization/delta closure;94draft saved,95unfinished.
All888source terms/1,044mappings remain source-closed. Older log entries below
describe earlier states; use the packet's main-audit.md and compact checkpoint.
**Validation/Git:** Independent promotion finding (empty evidence-form cue loss)
fixed with selected/held regressions;53focused tests and local source-range5tests
passed. Backend/tool compile, full suite1,140passed2skipped/149subtests and all
four HTTP200smoke routes passed. PowerShell launcher blocked by execution policy;
equivalent checks ran directly without changing policy. Existing progress edits
preserved. Fetch still fails
on malformed local refs/codex checkpoint; authenticated GitHub REST confirms
remote main matches pre-edit866dcd6. No ref deletion or credential retries.

### 2026-10-26 - Chapter91-95source phase closed; cue phase running
**Done:** All five source inventories independently reviewed and prepared:
91=304terms370mappings,92=164/180,93=116/140,94=163/189,95=141/165;
total888/1044. Six bounded source repairs in91/92closed; none93-95. All29owned
rasters/native emphasis/exclusions and actual title/column boundaries checked.
Source-wording Cysteine94andProtease95preserved.91UTI19free-text emphasis label
says table though actual repaired coordinates/text are a bold statement; recorded
minor metadata caveat rather than another source-freeze churn.
**Unfinished:** Strong authorMendel01a16f78-cf37-7721-bda2-09a3060080e7now phase2,
91decisions draft saved. Owns author/only; no final bank independently closed.
Main will review all cue/scope rows and target-specific alias notes, preserve
initial/first-valid/first-main files and recheck bounded deltas only. Source
inventory and canonical prior_before91freezes must not be regenerated over cues.
Next92-95cue drafts then integration/hold register/final tests. Stop95,96notstarted.
**Efficiency/Git:** Optional canonical alias adoption committed/pushed866dcd6,
local/remote matched0/0. Independent code finding repaired before freeze;62focused
tests and full local1,087passed2skipped/routes200; CI1,089passed. Code/tool hash
c2d60c2ee25db457c92ce4a87b362f29f7a1609955936f1f76b2618f8a47ea8cunchanged.
No measured tokens/net savings yet, no paid API calls or renders. Compact source
view retains all terms plus literal mismatches/exclusions/uncovered native bold,
not a semantic auto-admission tool. Normalized serialization baseline86-90is
505,558chars/998terms=506.57chars/term; whitespace/output bytes not billed tokens.
Local packet and report paths in prior entry; report still explicitly in progress.

### 2026-10-26 - Chapter91-95alias trial started
**Scope:** Fixed five chapters91-95, purchased renalPDF16-44,offset562; main
viewed all29owned rasters and actual title/column transitions. Source SHA unchanged.
Same authorMendel01a16f78-cf37-7721-bda2-09a3060080e7resumed, author/only;
phase1inventory91draft saved, all inventory closure/creative decisions pending.
Packet `Troubleshooting Prompts/tintinalli_chapter_cues_2026-10-26/batch91-95/`;
manifest and source cache ready. Main source review/exact preparation before
author phase2; do not overwrite a saved freeze or skip unfinished chapters.
**Efficiency:** Before authoring, optional canonical `aliases` adoption added to
generic sparse tool and documented. Explicit selected prior and target-specific
reason/comparison; code copies frozen cue/scope unchanged. No inferred synonym,
scope override, local alias, unselected prior or missing legacy scope adoption.
Independent reviewerMeitner01a17975-5241-72a3-b460-e384fae6497bclosed one array-
type finding after repair;62focused tests passed, including cross-chapter guards.
Tool frozen c2d60c2ee25db457c92ce4a87b362f29f7a1609955936f1f76b2618f8a47ea8c.
Tool-only full validation1,087passed/2skipped,compile and four routes HTTP200.
91source audit closed three bounded inventory repairs,304terms370mappings,
prepared againstprior_before91; correctedinventorySHA
67f3e2a8ee64c0942d48dbad9e0ee00460c1703b4f7cc151ff42318a9eccc440.
Reviewer closed; main remains non-author source/cue reviewer. No measured savings
claim, no cheaper creative-author trial, no paid API calls/renders. All cues
untested/nonproduction; previous holds remain. Stop95,96Abnormal Uterine Bleeding
not started (title checked in purchased TOC). Report in
`docs/chapter-91-95-sparse-workshop.md` remains explicitly in progress.
**Git:** Baseline cbac3f2, cleanmaintrackingorigin/main before edits. Authenticated
remote SHA matched; fetch still blocked by known malformed local Codex checkpoint
ref, not auth. No deletion/retry loop. Full validation/commit/push still pending.

### 2026-10-26 - Chapter86-90review and integration complete
**Done:** Resumed the existing stronger author, independently closed89three-row
and90four-row repair deltas; integrated88-90after the already closed86-87pair.
All998terms/1,135keyword mappings/27owned source rasters reviewed in this batch.
Final40different-bridge occurrences,126variants,831repeats,1hold; not unique
library growth, recall/render proof or production admission. Stop90; next91
Urinary Tract Infections and Hematuria has not started cue review.
**Preserved:** First author/first-valid/first-main freezes and bounded repairs.
29rows changed versus firstMAIN, including dependencies/provenance. Two88main
scope false alarms withdrawn unchanged after recovering full per-alias notes.
All1,129older core holds preserved, Bruit adds one:1,130occurrences/934distinct
terms. Primary76-entry catalog unchanged; no paid-provider calls or renders.
**Efficiency:**545.03combined authored bytes/term versus544.19previous batch,
not token measurement.447of625full semantic rows are unchanged repeats; no
demonstrated net savings. Future alias-adoption format needs separate testing,
not an undocumented mid-batch schema change. No new cheaper creative arm/cohort.
**Evidence:** `docs/chapter-86-90-sparse-workshop.md`; ignored packet
`Troubleshooting Prompts/tintinalli_chapter_cues_2026-10-25/batch86-90/`.
Final raw89b498cfea7217d42472cf4f571ec58b1ac487455b9f3689c0a0a6f204224e5015;
90d992f7c34776db2852b1429cc1b7aa1e6e87773d7306361387e844311d80f4ce.
**Validation/Git:** Backend compile,1,060tests passed/2skipped, including12hold
tests; four smoke routes HTTP200, server stopped. Hold check and old-core
preservation check passed. Commit/push follows; final SHA/remote/CI evidence
belongs in the closing response, not a self-referential commit hash here.

### 2026-10-26 - Resumed frozen86-90workshop
**Resume:** Same authorMendel01a16f78-cf37-7721-bda2-09a3060080e7running;
90draft checkpoint now saved (170of192rows at first check). No new cohort,
schema change, source scan or paid calls. Main remains independent reviewer.
88closed raw7d90cf1b1e8b22509f9f5321b3c061ef16482cef78e80b2576f1c17c8ee01dfe,
14new46variants225repeats; two main false alarms withdrawn after full alias
notes read. Ten changed88rows preserved, one self-corrected before main request.
89all142rows/152mappings plus57authored-repeat notes reviewed; exactly three
bounded corrections sent (joy/confetti and trembling-hand variants; existing
standalone tricycle repeat). FirstMAIN89hash
0783f7b0fb6f61afd81cfd9e20925fe2e46ce8536a3b09376bad672560637181preserved.
**Next:** Close89delta, independently review90, integrate88-90, regenerate holds,
finish report/metrics, run full validation, commit/push/CI. Stop after90.
Git stillmaintrackingorigin/main; authenticated remote remainsd41cb0f.
Earlier in-progress entry below is historical, not current completion status.

### 2026-10-25 - Chapter workshop86-90 in progress
**Scope:** Fixed five chapters86-90, offline only. Source inventories all closed:
998terms/1,135selected keyword mappings,27owned rasters plus blankGI90checked.
Two purchased source packets because unchanged sparse tool is single-source.
GIoffset472andrenaloffset562; source hashes/actual column transitions in
`docs/chapter-86-90-sparse-workshop.md` and ignored parent packet
`Troubleshooting Prompts/tintinalli_chapter_cues_2026-10-25/batch86-90/`.

**Closed/integrated:**86=9differentbridges21variants116repeats;87=4/31/198,
no new holds. Main independently reviewed all379cue/scope rows/432mappings;
9findings changed12rows, including dependencies. Late86consult alias correction
preserved earlier closure, no full repeat audit. Final raw86hash
0f6be6f17719f5b8ba606a5828fb86c9365556bdf97c7dce71b48ef73d36f7a9;
87hash690a1206756ccfb4195d831a761fb9decbf6636ec83980dbc024213b1f1a94b2.
Canonical pair integrated via reviewed-hash helper, not committed yet.

**Unfinished:**88/89/90inventories285/142/192terms and321/152/230mappings.
All prepared in `batch88-90`,prior_before88nowincludes86/87. Existing stronger
authorMendel01a16f78-cf37-7721-bda2-09a3060080e7resumed after usage pause,
owns only packet author/files and is authoring88then89then90. Main owns independent
review/integration; no new cohort. Do not reprepare over decisions or restart
source/old chapters. Stop after90;91not started for cue review. Preserve initials,
freezes, prior cutoff and bounded repairs. Main read-only exact-prose grouped
review view retains every term/prior mapping; no semantic auto-approval.

**Validation so far:**12hold tests passed; register current and all1,129older
core records preserved,933distinct terms. Test ranges extended through90with
new renal source SHA, so full suite must wait until all five banks integrated.
No provider/render/API calls, primary76-entry production catalog unchanged.
All cues untested/nonproduction. No measured token savings; no schema/tool change.
Separate$6imagebenchmark untouched. Source misread sponge-bolster lead disproven
and excluded; initial source/inventory repairs retained as effort.

**Git:**main tracksorigin/main atd41cb0fbaseline. Known malformed local Codex
checkpoint ref blocks fetch; authenticatedls-remote matched baseline. Do not
delete refs or retry credentials. Finish all five, validate, commit/push and prove
matching remote/CI before claiming synchronized completion.

### 2026-10-25 - Sparse chapter workshop81-85 completed
**Done:** Five-chapter offline source/cue workflow through Acute Appendicitis,
Diverticulitis, Bowel Obstruction, Hernias and Anorectal Disorders. Existing
stronger author Mendel resumed; non-author main reviewed all591materialized
cue/scope rows,700selected keyword mappings,29owned source rasters/native
emphasis, actual title/column boundaries, named tables/captions and bounded
prior-reference evidence. Fifteen main findings closed across16changed rows,
plus a separately preserved pre-main82semantic repair. Author completed and
closed. See `docs/chapter-81-85-sparse-workshop.md`.

**Results:**64different-bridge occurrences/89variants/438repeats/0newholds;
not64unique additions or tested learning/render success. All591candidates
untested/nonproduction, primary76-entry catalog and Forge unchanged. All1,129
older active hold core records preserved; register remains1,129occurrences/
933distinct terms. No old hold implicitly resolved by a retained alias.

**Efficiency:** Generic sparse tool unchanged.191minimal reuse rows,400full
semantic rows;242of the latter were unchanged repeats. Combined first-main
author bytes/term544.19versus461.47previously,17.9%higher, not evidence of
savings. Author-initial82 differs from first-main freeze and is preserved.
No additional cohort/advisor or weaker-creative-author equivalence trial. Future
explicit alias-adoption compression needs separately tested contract and review,
not automatic equivalence or a mid-batch schema change. No Anthropic/paid-provider
calls or renders; separate$6imagebenchmark untouched. Actual Codex usage not metered.

**Evidence:** Ignored packet
`Troubleshooting Prompts/tintinalli_chapter_cues_2026-10-25/batch81-85/`
preserves source/manifest, initials/freezes, prior/alias evidence, repairs,
main-first snapshots, metrics, main-audit, hash-bound approval and hold comparison.
Final85raw bank cad221c3279efaeddca713869d9e354d34fe6af6f3466fe3f2a3f4cfadef6823.
Main integrated through existing reviewed-hash helper. Source vocabulary,
clinical correctness, sound pronunciation, novelty and recall are not exhaustive
or experimentally validated. Agent01a16f78-cf37-7721-bda2-09a3060080e7closed.

**Validation:** Hold register current and1,129older core records preserved.
Full local backend compile,1,040pytestpassed/2skipped and four-route HTTP200
smoke passed; server stopped. No live provider or browser-generation validation.
Git/CI verification is separate against the final commit; known malformed local
Codex checkpoint ref prevented fetch, but authenticated ls-remote matched baseline
08a390e4dec4082dd3cf599aa6995aff5c41aaca. No ref deletion or credential retries.

**Next:**86Gastrointestinal Procedures and Devices, not started for cue review.
Do not restart81-85or erase freezes. Consider separately tested explicit alias
adoption before the next fixed five-chapter batch; retain stronger semantic
author/non-author review and bounded delta rechecks.

### 2026-10-25 - Sparse chapter workshop76-80 completed
**Done:** Continued five-chapter offline workflow through76Lower GI Bleeding,
77Esophageal Emergencies,78Peptic Ulcer Disease/Gastritis,79Pancreatitis/
Cholecystitis and80Hepatic Disorders. Stronger author Mendel resumed existing
context; non-author main checked all26owned source rasters/native emphasis,
829keyword mappings and748materialized cue/scope rows, plus bounded actual-prior
alias checks and repair deltas. See `docs/chapter-76-80-sparse-workshop.md`.

**Results:**135different-bridge occurrences/156variants/455repeats/2holds, not
135unique original additions or empirical recall/render evidence. All746selected
occurrences untested/nonproduction; primary76-entry catalog and Forge unchanged.
NSAID use nest/hearing-aid and Murphy-M/sign attempts held. All1,127older core
holds preserved; current register1,129occurrences/933distinct terms. No local
first-frozen hold resolved. Botanical source spellings/partial names retain
explicit uncertainty, not taxonomic or pronunciation verification.

**Efficiency:** Existing generic sparse tool unchanged;295minimal exact reuse
rows/453fullsemantic rows in first valid drafts. One bounded read-only advisor
Anscombe01a1711f-cc80-7f62-874d-70ff180adf7d suggested targeted observed-alias
supplement and compact hash-bound exception reports, now documented in workflow.
Author inventory/first-valid bytes per term461.47versus557.00previously,17.2%less,
NOT measured net token/billing savings. Different source density/chapters confound
comparison; advisor/main review/repair/evidence/integration still consume effort.
25post-first-valid changedrows(4/7/2/9/3), two prevalid local-reference statuses
and main's page28gutter preparation repair remain recorded, not hidden. Overnight
pause excluded from active-work claims. No paid-provider/Anthropic calls/renders;
separate$6imagebenchmark untouched. No weaker-model equivalence claim.

**Evidence:** Ignored packet `Troubleshooting Prompts/tintinalli_chapter_cues_2026-10-24/batch76-80/`
holds verified manifest/source, author freezes/initials/repairs/alias supplement,
main-first snapshots, main-audit, metrics, hash-bound approval and hold comparison.
Main integrated only final reviewed materializations via existing helper.
Author Mendel01a16f78-cf37-7721-bda2-09a3060080e7 completed; advisor completed and
closed. Source/clinical/vocabulary/corpus-novelty exhaustiveness not established.

**Validation:** Hold register --check/current and explicit old-hold core comparison
passed. Backend compile,1,020pytestpassed/2skipped and HTTP200four-route smoke
passed; smoke server stopped. Git/CI outcomes recorded in final verification;
no provider/browser-generation test performed in this offline task.
Auth works; fetch still hits known malformed local Codex checkpoint ref. Remote
SHA verified independently, no credential retry or ref deletion.

**Next:**81Acute Appendicitis, not started. Resume normal five-chapter cadence only
when requested. Reuse existing tooling; bounded singular/plural/head-only/older
attempt checks before creative accounting are the remaining useful refinement,
not a new whole-corpus census or a reduced independent-review requirement.

### 2026-10-24 - Sparse authoring trial74-75 completed
**Done:** Tested the recommended sparse authoring on74 Constipation and75 Upper Gastrointestinal Bleeding only. Same stronger author resumed; main independently reviewed real source and all185 materialized cue/scope rows. Separate non-author code lane reviewed materialization-core integrity/deltas. See `docs/chapter-74-75-sparse-trial.md` and the Sparse Authoring Contract in `docs/chapter-cue-workflow.md`. No production Forge/catalog/provider changes or empirical recall/image outcome.

**Measured:**185 terms/193keyword mappings,79 different-bridge occurrences/32variants/72repeats/2holds; not79unique additions. All183selected occurrences untested/nonproduction. Author inventory + first validated decision bytes per term874.65 ->557.00 (36.3% lower) versus72-73. Inventory phase306.5elapsed seconds for185terms versus918.3for401; first cue freezes5.7/9.0minutes into phase2. Different chapter sizes/topics and reusable-tool/test/code-review setup prevent net token/dollar or causal savings claims. Exact billed usage unavailable; no external paid calls/renders, separate$6benchmark untouched.

**Repairs:** One bounded round per chapter,4/1changed records: actual narrowing/neuropathy roots, metadata-only magnesium/bag variants recounted, stable blood/balance counted as state variant. Pre-freeze corrections preserved too: appearance-clause mapping, two74self-references and one75reference/scope issue. Existing1,125hold core records preserved; register1,127holds/931distinct terms. Neither local first-frozen hold resolved. Exact matching still misses aliases such as Strictures/narrowing; use bounded observed-miss retrieval, not whole-corpus census.

**Tool:** New `tools/chapter_cue_sparse.py` and35regression tests copy source metadata from selected span IDs, require explicit unchanged reuse, freeze source/prior evidence, reject source overrides/false selected copies/local cycles, preserve compact refs and require main hash-bound approval before integration. Missing legacy scope may be supplied explicitly without inventing a visual variant. Independent core review found positive-selection and changed-copy loopholes/bypass, now closed. Main separately reviewed/tested later integration/local-reference/legacy-scope helpers; do not claim entire final tool received a fresh full independent audit.

**Evidence:** Ignored packet `Troubleshooting Prompts/tintinalli_chapter_cues_2026-10-24/batch74-75/` has actual source regions20..26,7rasters/native spans/annotations, initial/validated/final decisions, metrics, code and source/cue reviews. First validated74sha55a80f34...8010f/75ac871901...c0c8; final decisions74ab6476cb...716ee/759f6dc418...623f. Full hashes in raw records/banks. Author Mendel01a16f78-cf37-7721-bda2-09a3060080e7 and code reviewer Beauvoir01a170f4-c688-7310-8726-d228426bac50 completed and closed. No source/clinical/vocabulary/corpus-novelty exhaustiveness claim; flattened highlighting uncertain.

**Verified:** Backend compile,1,000tests passed/2skipped, all four route smoke200, hold --check current and older-record preservation verified. Process-only PowerShell policy override; no global policy change. Known malformed local Codex checkpoint ref still blocks ordinary fetch; initial remoteSHA matched549888a and no destructive ref cleanup/auth retry loop was attempted. Final push/CI proof belongs in current task output/raw verification, not inferred from this log.

**Next:**76 Lower Gastrointestinal Bleeding, not started. This authorized trial stops after two. Reuse the sparse tooling/contract on the next requested batch; do not recreate closed74/75 or silently downgrade creative judgment. Standing default cadence remains five unless Patrick specifies otherwise.

### 2026-10-24 - Two-chapter upfront retrieval trial72-73 closed
**Done:** User requested only two chapters to evaluate the revised allocation. Completed72 Nausea and Vomiting and73 Disorders Presenting Primarily With Diarrhea. One stronger author, independent non-author main source/cue review. Same agent resumed after usage limit, saved first freezes retained; no restart/replacement cohort. See `docs/chapter-72-73-workflow-trial.md` for findings, examples, metrics and limitations.

**Results:**401 terms/467keyword mappings;185 different-bridge occurrences,53 variants,151 repeats,12 holds. These are not185 unique original additions. All389 selected occurrences remain offline/untested/nonproduction. All1113older hold core records preserved; register1125holds/929distinct terms. Meclizine andB12 local first-draft holds explicitly resolved, no older holds erased. Primary catalog/Forge unchanged; no external paid calls or AI image renders; separate$6benchmark untouched. Codex usage was consumed and hit a limit.

**Efficiency:** Frozen inventory -> deterministic exact-prior lookup BEFORE creative decisions -> compact decisions/common local assembler -> independent review -> bounded repairs. Both first drafts had zero held-with-selected-exact-prior flags, versus9leads (not9proven errors) in retrospective unchanged69/70first freezes. Still needed21/5changed decisions, chiefly accounting plus undefined adrenal alarm, unencoded static claim, wrong ileum host, duplicated peri/biliary-stone associations and overrigid holds. No net token/cost savings or cheaper-model creative equivalence established; preparation, sparse-format/tool setup and review count as work. Inventory15.3min elapsed, exact lookup0.54sec, first cue freezes14.2/22.1min into phase2. Multi-hour usage pause excluded. Next improvement: reuse tooling and let code copy selected-span metadata/inherit unchanged priors; model writes semantic deltas, not another full inventory/materializer. Not implemented as a silently changed trial arm.

**Evidence:** Local packet `Troubleshooting Prompts/tintinalli_chapter_cues_2026-10-24/batch72-73/`. Author Mendel=`01a16f78-cf37-7721-bda2-09a3060080e7`, completed/reviewed then closed. First decisions72b0d319c9...66f32 /73 6ed2f1dc...ecf30; final72fff6f4a0...b9b90f /73 07d07e9e...797cc. Full hashes in banks/main integration metadata and raw freeze records. Source GI PDF9-20 actual mixed-column boundaries, offset472,12rasters/native spans/annotations checked. No exhaustive clinical/vocabulary/novelty or empirical recall/render claim.

**Verified:**957repo tests passed/2skipped; compile + four route smoke200;200focused chapter/workflow tests and8local assembler tests passed; hold --check current. PowerShell process-only policy override needed, no global policy change. Existing malformed local Codex checkpoint ref blocked initial fetch; remote main SHA independently matched starting HEAD, no destructive ref repair/auth loop. Final push/CI evidence should be checked in current task output rather than inferred from this log.

**Next:**74 Constipation, not started. Do not automatically launch more chapters from this two-chapter task. Standing default remains five unless Patrick specifies a different scope. Do not recreate closed72/73 artifacts or claim measured savings from this observational trial.

### 2026-10-24 - Chapters67-71 closed with corrected association accounting
**Done:** Completed five source-grounded lexical banks:67 Tuberculosis,68 Pneumothorax,69 Acute Asthma/Status Asthmaticus,70 COPD,71 Acute Abdominal Pain. Three bounded stronger authors, cross-author nonauthor reviews67-68/69-70, main independent71 review and material corroboration. Resumed the same paused agents, no replacement cohort or paid provider. See docs/chapter-67-71-cue-review.md for findings, examples and caveats.

**Counts:**734 terms/1076keyword mappings;121 locally different association occurrences,7 variants,513 repeats,93 holds. NOT121 unique additions: parallel lanes used named1-66/canonical/workshop/supplement priors and several bridge families repeat across this batch. No exhaustive semantic novelty claim. Main normalized280 origin-only fields after independent semantic closure; that normalization did not change cues/scopes/association classes. A separately reviewed final exact-lookup delta restored two existing cues and deliberately retained the opioid hold. Old ingredient/reference counts are retained separately.

**Repairs:** Missed exact prior mappings, invalid no-inherited-approval hold gate, wrong anatomical/lexical heads, omitted meaningful emphasis/table/figure heads, false single-head keyword aliases, overcounted pyramid/weight/rhythm bridges.50 new-bank draft holds explicitly resolved with history; all1020 older active hold records' core fields preserved. Register now1113 occurrences/918 distinct terms. Remaining placeholder nonselections do not establish serious/exhaustive creative exploration. Primary76-entry catalog and Forge unchanged; all cues untested/nonproduction; zero paid calls/renders; $6 benchmark untouched.

**Efficiency:** Smaller helper provided exact-index GI support after one repair and tools/chapter_cue_prior_matches.py with14 tests. Read-only casefold reporting separates selected/held prior matches and clamps future cutoffs; human semantic/ingredient adjudication remains necessary. Workflow now requires that report before freezing. No measured dollar/token savings or equivalent cheaper authorship claimed.

**Evidence:** Ignored Troubleshooting Prompts/tintinalli_chapter_cues_2026-10-24/batch67-71/ contains source27-47/1-9 evidence, accepted preintegration hashes, first freezes, review/delta reports and main partial-integration recovery. A=01a16e0b-2f57-7bb1-8925-4c998f68495c, B=01a16e0b-4446-7641-8ca8-48b902b7532c, C=01a16e0b-587d-7aa0-a56e-bdb2e347517d, smaller=01a16e0b-ad9e-74e3-a211-ee55fb1d173a. All assigned reviews closed before integration. Original intermediate1cc71 materialization was not the final author freeze; actual preserved836a base is recorded in71 audit. A metadata integration stopped after67/68 on pending69 placeholder; preflight was fixed and known main-owned partial state resumed, no cue rollback.

**Validation:**203 focused chapter/keyword/hold/accounting/prior tests passed; final full suite949 passed/2 skipped/149 subtests; final note-delta keyword/accounting105 passed. Compileall and owned-server smoke passed with HTTP200 for `/`, `/forge`, `/library`, `/api/health`; smoke server stopped. Exporter current and all earlier hold core fields checked. Main runtime provider/browser/image behavior not exercised. Software checks are not recognition/recall/rendering evidence.

**Next:**72-76 starting Nausea and Vomiting; actual72 title verified at GI9 LEFT576.7, allRIGHT9 belongs72, offset472. Do not redo closed67-71 source/corpus audits or promote cues based on tests. Historical43 thumb/index issue remains a separate prior warning.

### 2026-10-24 - Association counting correction and bounded62-66 second look
**Done:** Recovered both paused author agents after queued inputs resumed despite initial usage-limit replies. Two disjoint29-record supplements, nonauthor review and main bounded integration. Canonical workflow now separates new_association/meaningful_variant/unchanged_repeat/hold from candidate/hold selection and existing-recount/reconsidered-attempt/new-revision origins. Seven-new headline from prior batch counted ingredient families, NOT all useful associations. No full1188-record reclassification claimed.

**Result:**24 supplemental candidates:17 existing candidate depictions recounted,3 selected revisions (epistaxis taxi simplification, rounded-knob net, departing weight),4 newly selected existing attempts (epinephrine packaging, ANCA anchor, rusty washer, crypt);5 still held. Association classes13/4/7/5 are local comparison judgments, NOT13 inventions. Main accepts reviewer over author's epinephrine hold, with nonunique taught device-category scope. Cyanide prior includes cyan/eye; Gemella prior phonetic reading is inference. Full report docs/chapter-62-66-association-second-look.md and independent review preserve limits/disagreements.

**Preserved:** Original chapter banks/holds/catalog unchanged; supplements do not silently resolve canonical holds or enter Forge. All untested; zero paid calls/renders; $6 untouched. Raw freezes/main materializer/checkpoint under Troubleshooting Prompts/tintinalli_chapter_cues_2026-10-24/association-second-look/. Authors62-64=01a16bec-11b5-7a11-bd16-9cd08a9b81e9,65-66=01a16bec-2689-7cf1-b64d-60327979ec99; nonauthor=01a16dfd-3de6-7d90-a873-4723bc7d8df7. No need to recreate these lanes.

**Validation:** Final full suite915 passed/2 skipped,149 subtests;17 focused workflow/supplement/hold checks passed; exporter current; original bank/hold/catalog diff empty; nonauthor bounded delta audit closed without new exceptions. Tests prove structure, not recall or image quality. Fetch still encounters the previously documented malformed local Codex checkpoint ref; authenticated remote HEAD matched64f4581 before edits, no destructive cleanup or auth retries. No browser/provider or new image validation.

**Next:** Continue67-71 with revised accounting; do not count a repeated prop as automatically old or a changed medical term as automatically new. Keep supplemental selections distinct from canonical holds unless explicitly integrating histories/register. No empirical reliability established.

### 2026-10-23 - Workflow routing and chapters62-66 cue batch
**Done:** Documented approved smaller-helper/stronger-curator split in docs/chapter-cue-workflow.md, AGENTS.md, CLAUDE.md, catalog and both delegation skills. Unchanged broadened rubric. Three drafting lanes; D62/63/65, main64 and B66 independent source/conceptual audits and repair rechecks. Totals: 1188 terms / 7 new / 1059 reused / 122 held; 1314 keyword mappings. Pulmonary source mixed-column regions checked; meaningful emphasized/table/figure lexical heads tried before exclusions. All earlier holds preserved.

**Limits:** AI editorial/source review, not human clinical, naming/recall/rendering evidence or exhaustive coverage. All candidates untested/nonproduction; primary catalog unchanged; zero paid calls/renders; $6 benchmark untouched.

**Verified:**171 focused chapter/hold/workflow tests passed; standard compile/test/smoke passed with912 tests passed/2 skipped and HTTP200 for `/`, `/forge`, `/library`, `/api/health`. All898 earlier active hold keys/reasons/attempts preserved; separate register now1020 occurrences/845 distinct terms. Chapter65 source-location enum corrected (16 bold-prose ->body,5 figure-caption ->figure_label); reviewed cue/hold/history/keyword/source data verified unchanged. Existing test rules were not relaxed.

**Next:** Chapter67 Tuberculosis, continue five-chapter cadence. Final validation/Git evidence in ignored batch62-66/main packet. Older43 thumb/index root remains flagged in prior handoff entry.

### 2026-10-23 - Paired lower-usage agent workflow trial
**Done:** User redirected unfinished62-66 batch to test cheaper delegation. Frozen two-source-excerpt/24-target paired trial: Luna medium vs Sol high, separate instruction-blind stronger reviewer, main corroboration, one repair maximum. Initial cue-workflow compliance7/24 vs24/24 (four substantive +13 minor issues in lean arm); after repair22/24 vs24/24. Final reference-head extraction70/70 both. See `docs/agent-workflow-pilot-2026-10-23.md` and ignored `Troubleshooting Prompts/agent_workflow_pilot_2026-10-23/` for original scores, precision sensitivity, hashes and limits.

**Judgment:** No equivalent end-to-end cue-authoring quality demonstrated. Smaller agents provisionally useful for bounded extraction/search/structured preparation; stronger cue curation/provenance/hold decisions remain necessary. No measured token/dollar savings; Codex account usage only, zero Anthropic/provider API calls/renders; $6 benchmark untouched. No app/Forge/provider code or primary catalog changes. No cue admitted or empirical recognition/recall/image result.

**Unfinished batch62-66:** Eight untracked62/64/65/66 JSON/MD draft files remain deliberately uncommitted;63 bank not yet present. Do not skip to67 or mark this batch complete. Raw packet `Troubleshooting Prompts/tintinalli_chapter_cues_2026-10-23/batch62-66/` preserves source27-page review, author builders and audit findings. A62/63=`01a1602b-198f-7960-aca9-b9e340a28ac9`, B64/66review=`01a1602b-2e99-7161-ad37-a7f8cd90aaf1`, C65/66=`01a1602b-4406-7122-a947-65dd6fe626db`, D62/63/65review=`01a1602b-5857-7e63-b76d-8f2bae98487b`; lanes closed for user-requested pilot, can resume when continuing batch.

**Resume checkpoints:**62 initial621ea627...aae71, all entries/targets read byD but full audit not finalized (history-check format normalization pending); bounded adding-machine root cleared.64 M64-1closed; M64-2 saved d5276f9e...9e1ba, main final delta recheck pending.65 D65-1..5 repairs saved d47abd1a...3814; post-repair author validation/four-term search trace and D delta recheck still pending.66 frozen2c40aa97...25764; B reviewed but final report unsaved, possible DNA/diaphragm/contrast/adding-machine/medicine-category findings not yet adjudicated. A63 unfinished. Latest completed/integrated chapter remains61; old43 thumb/index warning remains open.

### 2026-10-23 - Chapters57-61 five-chapter cue batch
**Done:** Same broadened rubric. Three drafting lanes; D57/58/60, main59 and B61 independent source/conceptual reviews, with reported repairs rechecked before integration. Totals: 1165 terms / 23 new / 1071 reused / 71 held; 1412 keyword mappings. Cardiovascular source actual71RIGHT-95, offset328; blank96 excluded. Meaningful lexical heads tried before statement/value exclusions. Earlier holds preserved.

**Limits:** AI editorial/source review, not human clinical, naming/recall/rendering evidence or exhaustive coverage. All candidates untested/nonproduction; primary catalog unchanged; zero paid calls/renders and $6 benchmark untouched.

**Next:** Chapter62 Respiratory Distress, continue five-chapter cadence. Final validation/Git evidence in ignored batch57-61/main packet.

**Older-bank follow-up:** Independent61 audit found that43's thumb record depicts an index finger.61 now uses an explicitly declared thumb-shaped variant of38's hand host;43 itself was not changed in this batch. Review that older root before reusing it as thumb-specific anatomy.


### 2026-10-22 - Chapters52-56 five-chapter cue batch
**Done:** User changed cadence to five, rubric unchanged. Three drafting lanes; non-author52/53/55/56 audits plus main independent54 review and integration. Totals: 1194 terms / 27 new / 929 reused / 238 held; 1355 keyword mappings. Actual Cardiovascular PDF34-71 mixed-column regions checked, including52 LEFT39 and53 RIGHT39. Meaningful emphasized/table/figure lexical heads tried; earlier holds preserved.

**Limits:** AI editorial/source review, not clinical currency, human-expert, recall or image validation. Partial-name/category ambiguity remains; no exhaustive coverage claim. Canonical catalog unchanged. No paid calls/renders; $6 benchmark untouched. Existing unrelated Forge edits remain unstaged.

**Next:** Chapter57 Systemic Hypertension, continue five-chapter batches. Final local validation and Git evidence in the ignored batch52-56/main run packet.


### 2026-10-22 - Chapters42-51 ten-chapter cue batch
**Done:** Four bounded drafting lanes; non-author cross-audits42-49 and main independent audit50-51. Reported definite repairs independently rechecked. Totals: 1,537 terms / 118 new / 1,288 reused / 131 held; 1,824 keyword mappings. Source Wound Management PDF19-61 offset266 and Cardiovascular PDF1-34 offset328; actual mixed-column/fullwidth chapter boundaries preserved. Literal Fibia/Pila, inferred classes and expanded/Greek aliases disclosed. Holds exported separately; earlier occurrences preserved.

**Limits:** AI editorial review, not human clinical, recall or image validation. Partial-name/category ambiguity remains; vibration/reverberation is a weak learned-category bridge. No exhaustive vocabulary or blanket semantic pass. Canonical production catalog unchanged (76). Zero paid calls/renders; $6 benchmark untouched. Prior pending notes superseded by final integration sections.

**Next:** Chapter52 Syncope, ten-chapter cadence. Preserve pre-existing unrelated Forge edits unstaged. Final validation/Git evidence recorded in local run packet.


### 2026-10-21 - Chapters39-41 wound vocabulary batch
**Done:** Three bounded AI chapter drafting lanes plus independent main
source/cue integration.39=74terms/21new/48reuse/5hold;
40=64/26/34/4;41=102/20/67/15. Total240terms/67new/149reuse/24hold;
340 keyword term/page mappings. No paid-provider calls or mnemonic-image renders;
$6 benchmark allowance untouched. All reviewers completed; no lost lane.

New source Tintin_Wound Management.pdf,62pages,
SHA256691e464e103295d5b27bf4173a60fa6a86e81261cdeb35f2c9b45411ea4c8119,
printed offset266. Actual boundaries verified visually and by coordinates:
39=1-3 upperleft3;40=lowerleft3+allright3 through fullwidthFigure40-5/upperleft6;
41=lowerleft6+right6 below40figure through fullwidthFigure41-19/leftrefs19.
Right6 Overview/Table41-1 precedes actualleft41title vertically; do not exclude
it by horizontal title-height clipping. Adjacent42 lowerleft/right19 excluded.
Annotations1-19 empty; typography and table/figure names checked separately.

Main checked every recorded term/page, keyword mapping, cue/attempt and actual
prior ingredient/target. CI and sutured use actual source forms; expansions
explicit. Raney comes from body clips (Raney), not invented contiguous phrase.
The one substring-check flag linear lacerations is an explicit shortened alias
from linear, nonfacial lacerations, independently verified on raster14.
Full clinical/numeric/procedural assertions excluded only after lexical heads.

Shared closure, loupes, mattress, CT/MRI, scalp and infection roots reconciled;
old sutures, forceps, foreign-body, skin, gut, sponge and material ingredients
reused. Bloodless/control maps clamp/pipe, not leaking pipe alone. Familiar
categories and economical partial-name ingredients retained without requiring
unique blind decoding. Product/name fragments may collide: tetra, key, deck,
butter, cap, suture and adhesive families need later contextual discrimination.
No clinical material properties, procedure geometry or product equivalence claim.

Seven added decision histories preserve all older holds/rejections. Separate
register refreshed/check-current:458 active occurrences/379 distinct terms/
70 histories. Explicit comparison proves all434 previous occurrences preserved.
Resolved JSON reuse graph88nodes has no cycle/held target; legacy non-fragment
links terminate traversal. Canonical visual catalog remains76, unchanged.

**Verified:** focused203passed/1skipped; full pytest835passed/2skipped/
149subtests; compileall backend; catalog valid76; deterministic held register
current; whitespace check clean. No browser/server/provider generation test.
**Known risks / NOT verified:** bounded lexical screen, not exhaustive chapter,
clinical entailment, credentialed-human, pronunciation, naming, recall or
mnemonic-image validation. All chapter entries untested/nonproduction; evidence
empty. Preexisting one-line Forge HTML/pipeline edits preserved unstaged.
Fetch failed once on existing malformed local Codex checkpoint ref; auth works,
GitHub API matched starting HEAD2c59b2c. No ref deletion/credential retry loop.
Main owns final commit/push and remote-SHA verification.
**Next:**42 Face and Scalp Lacerations, actual title verified on19, not yet
cue-reviewed. Continue with the same source/emphasis/reuse/hold workflow.

### 2026-10-21 - Chapters36-38 vocabulary batch and reviewer recovery
**Done:** Three disjoint AI chapter drafting lanes plus independent main
source/cue integration.36=115terms/39new/49reuse/27hold;
37=139/32/67/40;38=144/49/43/52. Total398terms/120new/159reuse/119hold;
604 keyword term/page mappings. Reviewers36/37 hit a Codex usage limit and were
revived from saved checkpoints at Patrick's request; both completed. No Anthropic
funding error, API/provider call, image render or benchmark-budget spend.

Main checked every recorded vocabulary/page, keyword mapping, cue/attempt and
actual prior ingredient/target. Verified source hash, mixed-column boundaries8/20,
full-width Figure36-20 and nonblank final38; all annotation lists8-38 empty.
Wheal page corrected13, not12. Full-row/heading aliases and quote/line-wrap
normalization are explicit, not invented contiguous quotes. Added missing bold
hypnotic/amnesia and Rigid Chest Syndrome trials before final integration.

Main challenged overly rigid holds under Patrick's broad learned-category rule:
glucose meter, open-fracture model, amplified pain, toilet metaphors and simple
word fragments may be candidates without unique diagnosis/full-name recovery.
Old vessel/cuff/finger/ear, fluid/duration/bolus/bag-valve, spinal-cord and
radiograph ingredients reused, not new-counted. Deck/dex, kettle, fan and
spinning-top name collisions explicitly require later contextual discrimination.
Resolved JSON reuse graph has no cycles/held targets; legacy non-fragment links
terminate traversal.30 added histories preserve earlier attempts and holds.

Separate held register refreshed/check-current:434 active occurrences/360 distinct
terms/63 decision-history records. Canonical visual catalog remains76 unchanged.
Data tests extended through38; five invalid figure source-type labels corrected
to existing figure_label schema instead of weakening tests.

**Verified:** focused194passed/1skipped; full pytest826passed/2skipped/
149subtests; catalog validation76; deterministic hold register current;
source-location diagnostic no remaining misses; diff whitespace checks clean.
No server/browser/provider test required for this docs/data-only scope.
**Known risks / NOT verified:** bounded lexical review, not exhaustive chapter or
clinical coverage. AI review is not credentialed-human, pronunciation, object
naming, recall or mnemonic-image validation. All tested:false, production false,
evidence empty. Preexisting Forge HTML/pipeline one-line edits preserved unstaged.
Fetch still fails on the existing malformed local Codex checkpoint ref; auth works
and remote GitHub API matched starting HEAD61219cd before integration. No ref
deletion or credential retries. Main owns final commit/push/remote-SHA proof.
**Next:** Chapter39 Wound Evaluation, confirmed in supplied TOC and opening of
Tintin_Wound Management.pdf, not yet cue-reviewed.

### 2026-10-21 - Chapters33-35 vocabulary review and source-PDF transition
**Done:** Three disjoint AI drafting lanes; main checked every recorded word/page,
keyword location, cue and resolved reuse reference.33=131terms/38new/75reuse/18hold;
34=84/21/53/10;35=125/40/37/48. Total340terms/99new/165reuse/76hold;
421 keyword term/page mappings, not421 novel words. Bounded emphasis/table/figure
screen, not exhaustive vocabulary, clinical entailment or empirical recall proof.
**Source:**33/34 Resuscitation Procedures hash unchanged, +142offset.34 includes
final PDF86.35 Analgesia/Anesthesia/Procedural Sedation PDF1-8, +228offset,
SHA256 dc0444f631bf8c0dc22c3a6d67cfce06f8e3945c6e019bb0a7b892c4b1e841fb.
Mixed-column boundaries74/81/analgesia8 verified. Raster QRS/P-wave/atrial-pace/
ventricular-pace labels78/79 visually checked. Drug-seeking conventional hyphen
preserved across line wrap. No assigned-page annotations; printed emphasis checked.
**Revisions:** Main's pear/cardigan, cool-tuber and mu/cow proposals challenged;
partial-name/context limits explicit, no clinical procedures or medication effects
encoded. Topic-only pacing reuse for transesophageal/epicardial corrected. Older
esophagus, sick-sinus, pad, QT, agitation and rigidity families reconciled.35 ket-
family collisions must be disambiguated before actual lesson use.34 hemodynamics
uses verified12 pump ingredient;32 actual cue is monitor-only, not a red pump.
**Holds:**315 active occurrences/259 distinct terms;33 decision-history records,
including9 new local histories. Older chapter/workshop holds remain unchanged.
Canonical catalog76 unchanged; zero paid calls/Forge/images; $6 allowance untouched.
**Validation:** Focused185passed/1skipped; hold register current; catalog valid76.
Full suite817passed/2skipped/149subtests passed; staged whitespace check clean.
Resolved JSON reuse chains checked without cycles/held targets; legacy
non-fragment links terminate traversal. No provider/browser, human-expert,
recall or image validation.
**Next:**36 Local and Regional Anesthesia, actual title right analgesiaPDF8.
Earlier1-19 emphasis backfill outstanding. Preexisting checkpoint-ref fetch issue
persists; no ref deletion/auth retry. Preserve unrelated Forge HTML/pipeline edits.

### 2026-10-20 - Chapters30-32 vocabulary batch and reviewer revival
**Done:** Three AI drafting lanes; main independently checked every recorded
vocabulary/page and keyword location, all cues and resolved reuse targets.
30=93 terms/32 new/46 reuse/15 hold;31=150/68/53/29;
32=91/41/48/2. Total334 trials/141 new/147 reuse/46 hold;
404 distinct keyword term/page mappings after merging four duplicate same-page
records without losing emphasis notes. Rendered boundaries52/58/59/69/70/74
verified; palmar arterial arches68 verified inside embedded raster. Full-width
Table32-3 and right-top continuation included;33 lower-right74 excluded.
No assigned-page annotations; printed typography checked separately. Not
exhaustive vocabulary, clinical/source-entailment, human-expert or recall proof.
**Reconciliation:** Scalpel/Seldinger root30; guidewire/gauze root31. ECG/lactic
acidosis reuse older records. Modern JSON reuse chains checked without cycles
or held targets; legacy non-fragment links terminate traversal. Generic label-T
removed from lactate cue. ABG/AAA, seize/seizure and mitochondrion-model main
proposals independently challenged/accepted with context limitations. Nine local
decision histories retained, older holds/rejections unchanged. Batch-level31
reconciliation history moved outside term-specific resolved_holds.
**Holds:**239 active chapter occurrences/191 distinct terms;24 decision-history
records. Fixed exporter to preserve explicit attempted_cue; regression added.
**Interruption:** Revived31 reviewer after Codex usage limit; not Anthropic
funding. Saved drafts preserved; no paid calls or image/Forge runs. $6 allowance
untouched; canonical catalog unchanged76. Preserve unrelated Forge edits.
**Validation:** Focused176passed/1skipped; hold register current; catalog valid76.
Full suite808passed/2skipped/149subtests passed; staged whitespace check clean.
No browser/provider/recall/render validation.
**Next:**33 Cardiac Pacing and Implanted Defibrillation, actual title right74.
Earlier1-19 expanded emphasis backfill still outstanding. Preexisting malformed
Codex checkpoint ref still prevents fetch; no ref deletion or auth retries.

### 2026-10-20 - Split source chapters29A/29B vocabulary review
**Done:** Two disjoint drafting agents plus main independent source/cue review.
29A=184 terms/59 new/82 reuse/43 hold;29B=71/30/29/12.
Total255 trials,89 new candidate compositions,111 reuses,55 holds;
282 keyword mappings include aliases/repeated emphasized words, not additional
discoveries. Main independently checked every entry/keyword source location,
all cues and reuse targets, visually inspected boundaries37/48/51/52 and raster
Insp. Hold label. Five29A source normalizations documented explicitly. Dropped
unneeded tidal/cascade/limb modifiers from broader reuses; repaired incomplete
leak/opening cue descriptions. Lid/cane, Midas/lamb, sawing-logs and saturated-
sponge/oxygen proposals challenged/accepted by drafters. No empirical validation.
**IDs:** Preserve source29A and29B as actual string IDs, not integer29 alias.
Hold-register tool naturally orders numeric/suffix IDs, rejects malformed IDs,
and preserves split holds separately. Added ordering/duplicate/invalid-ID tests.
Within-bank reuse must target a different retained candidate, not itself or a
within-bank chain. Previous integer29 next-chapter note is superseded.
**Holds:**193 active occurrences/153 distinct terms;15 resolution histories,
including four new local reconsideration records. Older chapter/workshop holds
remain, including28 PEEP. All candidates untested and outside canonical catalog.
**Validation:** Focused tests166passed/1skipped; hold register current; canonical
catalog valid76 unchanged. Full suite798passed/2skipped/149subtests passed.
Staged diff whitespace checked before commit. Zero paid calls/images;
no Forge, current-clinical-guidance, human-expert, recall or image validation.
$6 benchmark budget untouched. No assigned-page PDF annotations; fonts/visual
checks separately assessed printed emphasis, not exhaustive chapter coverage.
**Next:**30 Surgical Airways, actual title PDF52. Earlier1-19 expanded emphasis
backfill still outstanding. Fetch checkpoint-ref issue persists; no deletion or
auth retries. Preserve unrelated Forge HTML/pipeline edits.

### 2026-10-20 - Chapters26-28 emphasized vocabulary continuation
**Done:** Two disjoint AI drafting lanes plus main independent integration.
26=63terms/24new/21reuse/18hold;27=42/29/6/7;28=98/51/28/19.
Combined203 term trials:104 newly recorded candidate compositions,55 reuses,
44 holds;212 linked keyword items include9 explicit aliases. No claim of novel
invention, exhaustive vocabulary or clinical coverage. Main checked every entry
and keyword location within actual chapter regions, rendered mixed-page
boundaries, all cues and resolved reuse targets. Source hash unchanged, +142
printed offset. Chapter28 excludes entire Table29A-1 on PDF37 right column.
No assigned-page PDF annotations; fonts and visual checks separately reviewed
printed emphasis. Shared-word and trademark normalizations explicit.
**Revisions:** Main-proposed hippo/oath gesture, ECG equipment and four familiar
device-category cues independently challenged/accepted by drafters. Inflammatory
family and sedation reused from same-batch26; older holds remain. Seven draft
hold resolutions preserve initial attempts/reasons. Register now138 active hold
occurrences/111 unique terms,11 explicit resolutions including prior history.
Candidates remain untested and outside the unchanged76-entry production catalog.
**Validation:** Focused cue/keyword/hold/workshop/catalog tests152passed/1skipped;
hold snapshot current; canonical catalog valid76. Full suite784passed/2skipped,
149subtests passed. Staged diff whitespace checked before commit.
No Forge runs, images, clinical/legal or human-expert validation. Zero paid API
calls/renders; separate $6 benchmark budget untouched.
**Next:** Tracheal Intubation, actual source chapter29A (PDF37). Ledger uses
integer29 for current schema compatibility; do NOT skip subsequent29B Mechanical
Ventilation. Earlier1-19 still lack expanded emphasis-screen backfill. Fetch again
failed on preexisting malformed local Codex checkpoint ref; no ref deletion or
credential retry. Preserve unrelated Forge HTML/pipeline changes.

### 2026-10-20 - Resumed Chapters20-25 with emphasis screen
**Done:** Resumed interrupted AI drafting lanes after Codex usage-limit interruption,
not an Anthropic funding error. Added explicit bold/semibold, heading, highlighted
annotation and meaningful table-keyword screening per user request. No annotations
found in relevant source ranges; printed emphasis handled separately.275 term
records:137 new candidate compositions/78 reuses/60 holds;262 linked keyword items
include2 cross-bank referrals.20=33/11/8/14;21=55/28/11/16;22=48/37/7/4;
23=44/34/9/1;24=54/12/31/11;25=41/15/12/14 (terms/new/reuse/hold).
Main separately checked source locations, actual chapter boundaries, cue scope and
same-batch reuse. Word-sharing normalizations documented, not falsely called exact
contiguous quotations. Main-proposed vase-in-press and cyan-eyed eye challenged
by drafter; detached paddles/bolt separately challenged by another AI reviewer.
Not credentialed human, clinical or empirical validation. Older pending notes are
superseded by dated main-integration sections, not rewritten as independent work.
Persistent register now94 hold occurrences/70 distinct terms; historical holds and
cyanide revision retained. Chapter1 defibrillation hold remains flagged with later
retentions. Earlier1-19 samples have NOT had emphasis-screen backfill.
**Validation:** Full pytest775passed/2skipped/149subtests; focused
cue/keyword/hold/catalog tests143passed/1skipped; hold
snapshot current and canonical catalog valid76entries, unchanged. No paid calls,
clinical lessons, Forge runs or images; $6 benchmark allowance untouched.
**Next:** Chapter26 Post-Cardiac Arrest Syndrome, not started. Fetch previously
failed on a malformed local Codex checkpoint ref; no credential retries or ref
deletion. Preserve unrelated Forge HTML/pipeline edits outside this batch.

### 2026-10-19 - Repeated batches14-16 and17-19
**Done:** Two further chapter-bounded runs.14=16terms/8new/4reuse/4hold;
15=17/9/6/2;16=13/10/3/0;17=16/6/9/1;18=16/6/8/2;19=12/7/1/4.
Combined90terms/46new compositions/31reuses/13hold occurrences, not90novel
terms or comprehensive coverage. Long17/18 sampled for selected vocabulary.
**Review:** Three disjoint drafters, main independently checked all90 term/page
matches, source types, actual rendered boundaries and cues/reuse. Main-proposed
glue-gun/glucagon and excess-carb/hypercarbia separately challenged; main snail
and wolf-parking refinements challenged by drafter, not user-originated.
Long-QT18 source corrected to Table18-27; Greek beta19 normalized. Existing
holds not silently resolved. Register now34chapter holds/27unique terms,3resolved.
**Validation:**131focused tests passed/1skipped; hold register current; catalog
valid76; diff clean. No clinical, image-recognition or recall validation, no
backend/browser/provider run. Zero paid API calls/renders; $6 untouched.
**Source:** Same Resuscitation hash and +52offset; boundaries PDF16/21/26/29/
47/71/81 visually checked by main. No full text or PDFs committed. Canonical
catalog unchanged. Next20 Pharmacology of Vasopressors and Inotropes, title-only.
Preserve unrelated Forge edits. Fetch checkpoint failure persists; verify push
using authenticated remote API SHA/ancestry. Continue refreshing hold register.

### 2026-10-19 - Persistent hold register and Chapters11-13
**Done:** User explicitly requested separate list of every held chapter word.
Added generated docs/tintinalli-held-cues.json/.md and offline stdlib builder
tools/chapter_cue_holds.py --write/--check with stale-snapshot tests. Chapter1
current broadened decisions transcribed to structured JSON without new review;
original strict ledger preserved. Explicit resolved history for CPAP, bicarbonate,
sulfonylureas;21active chapter holds/20unique terms through13,3resolved holds.
**Batch:**11=16terms/10new/4reuse/2hold;12=17/9/7/1;13=17/8/8/1.
Total50terms/27new/19reuse/4holds (tranexamic repeats prior Chapter7 hold).
**Review:** Separate AI source/cue review for11; main independently checked
worker12/13 source matches, visual boundaries and cues. Crystalloid13 changed
to reuse12, not duplicate discovery. Capillary-refill action made single-state.
**Limits:** Zero paid calls/renders, $6 benchmark untouched, catalog76 unchanged,
all cues untested/no production admission. No clinical guideline endorsement.
Resuscitation PDF hash d644c7ff121f44da8684b9c5cb3e0e69c5b66aa391dd5bcb9d5e4789023c3b69;
PDF+52 printed. Next14 Allergy and Anaphylaxis, title only, not reviewed.
**Validation:**125focused tests passed/1skipped; hold register current; catalog
validator valid76; diff check clean. No full backend/browser/provider trial.
Preserve unrelated Forge edits. Fetch checkpoint failure persists; verify Git
push through authenticated API/ancestry. Refresh hold register each batch.

### 2026-10-19 - Chapters8-10 offline cue review batch
**Done:** User requested next several chapters; bounded scope to8-10.
Chapter8:18terms/12new/4reuse/2hold; Chapter9:16/10/4/2;
Chapter10:18/13/4/1. Total52terms,35new compositions,12reuses,5holds.
**Review:** Main authored8, separate AI reviewed source/concepts. Disjoint
workers authored9/10; main independently verified all term/page matches and
visual boundaries and reviewed cue decisions. Sulfur eggs reused; blue-color
collision between methylene/Prussian documented, not uniquely identifying.
**Validation:** Focused chapter/workshop/catalog tests119passed/1skipped;
catalog validator valid76; diff check clean. No backend/browser/provider trial.
**Limits:** All untested, no production admission, catalog76 unchanged, zero
paid calls/images, $6 benchmark untouched. No current clinical validation.
Source PDF/hash same;8 PDF17-23,9 PDF23-29,10 PDF29-34, printed offset18.
Next11 Sudden Cardiac Death (TOC only), source review not started. Corrected
old Chapter7 camera-lens workshop reference filename during provenance check.
Unrelated Forge edits preserved; fetch checkpoint failure persists, auth works;
use remote SHA API and ancestry checks for push verification.

### 2026-10-19 - User sulfur cue and Chapter7 vocabulary review
**Done:** Retained Patrick's rotten-eggs/stink cue for sulfonylureas as learned
sulfur/sulfon partial-name bridge, not drug odor, chemistry or allergy advice.
Chapter6 counts now14new/4reuse/0hold; original13/4/1 historical entry preserved.
Chapter7 twenty terms:14new compositions,5reuses,1hold (tranexamic acid).
**Verified:** Main visual title boundaries PDF12-17/printed30-35; same source
hash; independent AI source/concept review verified20 term/page matches and
supported user cue. Integrated readable lens/retina/skin/volume refinements.
**Limits:** No clinical, render or recall validation; zero paid calls/images;
catalog76 and $6 allowance unchanged. Unrelated Forge edits preserved. Fetch
still fails existing checkpoint ref, authenticated GitHub API/push verification
used. Next Chapter8 Chemical Disasters; adjacent boundary text excluded.

### 2026-10-19 - Chapter 6 Natural Disasters candidate bank
**Done:** Eighteen selected terms:13 newly recorded untested candidates,4reuses,
1hold. Vector-arrow mosquito, waterborne boat, nonunion wedding/bone characters,
external scaffold and familiar actions retained. Sulfonylureas held, not forced.
**Verified:** Same Disaster Management source hash; PDF7-12=printed25-30;
main visually verified shared title boundaries. Independent AI source/concept
review supported all term pages; main integrated visible posture and scaffold
connection improvements. No rendered, clinical or learning-effectiveness proof.
**Limits:** No paid calls or images; $6 allowance untouched; catalog76 unchanged.
Unrelated Forge edits preserved. Fetch failed on existing Codex checkpoint ref;
GitHub auth works, push requires remote API verification. Next Chapter7 Bomb,
Blast, and Crush Injuries, not reviewed beyond boundary/title identification.

### 2026-10-19 - Chapter 5 Disaster Preparedness candidate bank
**Done:** Eighteen source-grounded terms:12 newly recorded untested candidates,
5reuses,1hold. Blood vault/bank, crossed matches, push/pack and rice-in/ricin
name bridges retained alongside familiar category cues. Phosgene held, no forced
fragment. Same learned tree/PPE/overflow vocabulary reused.
**Verified:** Disaster Management source hash, PDF1-7=printed19-25, visual title
boundaries,18 term/page matches, independent AI source/conceptual review and
focused data tests. Source prose/heading only; no clinical or efficacy validation.
**Limits:** No paid calls, images or recall tests; $6 allowance untouched.
Canonical catalog76 unchanged. Unrelated Forge edits preserved. Fetch checkpoint
error persists; remote API verifies Git push SHA. Chapter6 text exposed during
boundary extraction excluded. Next: Chapter6 Natural Disasters, not started.

### 2026-10-19 - Chapter 4 Mass Gatherings candidate bank
**Done:** Sixteen terms:13 new untested chapter candidates,2 reuses,1 hold.
Doctor/director, ant/acid, astronaut/space blanket and parrot/repeater retained
alongside useful literal/category cues. Cardiac arrest and nitro cues reused.
**Verified:** Source hash, pages13-18 boundaries, all16 term/page matches
(8 prose/heading,8 table), independent AI source/conceptual review and focused
data checks. No clinical, legal, image, pronunciation or recall validation.
**Limits:** No paid calls or renders; $6 benchmark untouched; canonical76 catalog
unchanged. Existing unrelated Forge edits preserved. Fetch checkpoint failure
persists; remote API used to verify push SHA.
**Next:** Chapter5 Disaster Preparedness, title verified in TOC only, not started.

### 2026-10-19 - Chapter 3 Air Medical Transport candidate bank
**Done:** Sixteen terms, fourteen retained untested chapter compositions and two
holds; broad category, familiar state and wordplay cues accepted. Flail/treasure
chest and boy/judge are name bridges, not clinical explanations. Ledger/index
updated; Chapter 4 Mass Gatherings next, not started.
**Verified:** Source hash, all term/page matches (9 prose,7 table), visual boundary
inspection pages9/13, independent AI source and conceptual review. Focused data
tests and catalog validation; no clinical claim, image or learner validation.
**Limits:** Some generic grammar reused; not fourteen novel inventions. No paid
calls or renders, $6 budget untouched, canonical catalog76 unchanged. Initial
extraction exposed later chapter text but it was excluded. Unrelated Forge edits
preserved. Known fetch checkpoint error persists; remote API verifies push SHA.

### 2026-10-19 - User calibration: useful category cues, not exhaustive specificity
PPE was already retained; simplified to familiar hazmat suit with optional shield
exaggeration. Retained orange baking-soda box for bicarbonate and bellows as broad
positive-pressure support recall cue (not mode discrimination). Chapter 2 now has
12 new candidates, 1 reuse, 3 holds. Original review preserved in report; these two
decision changes were not independently re-audited or empirically tested.
Updated catalog guidance: hypothetical alternatives alone do not veto familiar
cues; match specificity to what is actually taught. No paid calls or renders.

### 2026-10-19 - Chapter 2 vocabulary/cue review only
**Done:** Added Chapter 2 Prehospital Equipment candidate bank/report and ledger
link. Sixteen terms: ten new untested designs, one reused magnesium cue, five
holds. Broader method preserved; no production catalog or Forge changes.
**Verified:** Actual PDF pages 3-9, SHA256, all sixteen term/page matches; main
visual boundary inspection plus independent AI source/conceptual review. Focused
data/catalog tests and diff checks run. No clinical-fact or learner validation.
**Limits:** Chapter 3 remains unstarted; source text incidentally extracted from
page 10 was excluded. No paid provider calls/renders; $6 benchmark untouched.
Fetch continues to fail on known checkpoint ref; remote API used for SHA checks.
Existing unrelated Forge modifications preserved and excluded from commit.
**Next:** Chapter 3 Air Medical Transport when requested; retained designs still
require cue recognition, discrimination and recall checks before production use.

### 2026-10-19 - Broadened Chapter 1 cue re-audit after user correction
**Done:** Added `docs/chapter-1-broadened-cue-audit.md`: same ten source-verified
terms, six conditional candidates and four holds. Expanded discovery beyond
exact sound assembly to phrase play, double meanings, actions and relationships.
Preserved original zero-proposal ledger and independent-review disagreements.
Updated chapter guide and catalog guide; canonical 76-entry JSON is unchanged.
**Verified:** Independent AI conceptual challenge, focused catalog/workshop tests,
and diff hygiene. No new PDF/source, medical-claim, rendering or recall validation.
**Limits:** No production changes, Forge run, paid calls or images; $6 benchmark
budget untouched. Existing unrelated Forge edits preserved. Fetch still fails on
the known Codex checkpoint ref; do not claim a successful fetch.
**Next:** Test selected candidate recoverability against distractors before
production use; Chapter 2 remains unstarted. Do not resume phonetic-only filtering
as a veto on all conceptual mnemonic vocabulary.

### 2026-10-19 - Actual Tintinalli chapter review; ONE CHAPTER at a time
Patrick redirected the proposed broad source pass to one chapter at a time.
Stopped Chapter5-10 and11-21 agents; their early local partial artifacts are
cancelled/notused,not completed progress. Finished only Chapter1 Emergency
Medical Services using actual Tintin_Prehospital Care.pdf pages1-3.
Important boundary:page3's runningheader saysChapter2,butCh1continues through
leftcolumn/upperright toreferences beforeactualPrehospitalEquipment title.
Text+visual checks and independent AI audit confirm that boundary.

Ten selected terms screen complete:9 bodymatches,one chapter-title-onlymatch
(EmergencyMedicalServices). Zero association proposals/admissions underunchanged
strictcriteria. Not exhaustive vocabulary orproofno mnemonicpossible.
No PDFs/fulltextcommitted; only shortterms,sourceSHA,page refs,screen reasons
in docs/tintinalli-chapter-cue-ledger.json and readable tintinalli-chapter-cues.md.
Rawplan/supersededplan,local sourceaudit and boundaryPNG under
Troubleshooting Prompts/tintinalli_chapter_cues_2026-10-19/.
Chapter2 PrehospitalEquipment is next/notstarted forcue review; don'tbatchahead.
No provider/API/render calls; $6 benchmarkcap untouched; primarycatalog76 unchanged.
Existingtwo unrelatedForgeeditsleftuntouched. Gitfetchknowncheckpoint error;
remote main matchedlocalHEAD throughauthenticatedGitHubAPI atstart.
Validation:all10 term occurrences checked against actualchapter boundaries;
independent sourceaudit confirms9body+1title. Ledgerintegrity checkpassed;
focusedcatalog/workshoptests109passed,1skipped. Primarycatalogschema76valid.
No fullsuite/browser/provider/image/recall validation performed for this docs-only
chapter record. Do not present offline tests as mnemonic-effectiveness evidence.

### 2026-10-19 - Sound-bridge workshop 2; unchanged strict criteria
Patrick requested another bounded run. Saved plan max60 attempts,20 per lane,
prior terms excluded,no quota,no paid calls or extra delta batch. Three AI lanes
stopped at26 distinct new terms rather than padding:anatomy10,signs8,lab8.
Independent AI reviewer screened all11 shortlisted terms:4 retained,7 held.
Other15 were rejected by proposal lanes,not independently re-adjudicated.
Added only balloon,lens,iron,tapeworm to offline primary catalog (now76 entries:
58 candidates,17 legacy_unverified,one restricted). Three are shared-headword
polysemous cues; tapeworm is a constructed compound rebus. No medication cue
survived. No changes to earlier decisions,first workshop JSON or production JS.

New durable bank/guide:docs/sound-bridge-workshop-2.json and .md. Raw plan,
incremental proposals,eligibility checks and independent review:
Troubleshooting Prompts/sound_bridge_workshop2_2026-10-19/.
All26 terms checked against baseline concepts/aliases,earlier103-term workshop,
and initial24-term wordplay packet; no conflicts. Extended tests across both
banks:unique terms,combined retained-only catalog membership,exclusion/bounds
checks,and held/rejected exclusion. Source checks limited to headwords/sounds
and scope in Collins,NCI and MedlinePlus; no clinical lesson facts imported.

No human specialist signoff,images,naming/recall trial or reliability gain claimed.
Zero Anthropic/provider/render calls; future$6 benchmark allowance untouched.
Existing2 unrelated Forge edits remain unstaged. Fetch still fails on the known
Codex checkpoint ref; authenticated GitHub API matched remote main/local HEAD.
Validation:catalog76 valid; focused109 passed,one skipped; final full suite741
passed,two skipped,149 subtests passed (51.61s). Prior workshop JSON unchanged.
These are offline integrity/regression checks,not image or learning validation.

### 2026-10-19 - Sound-bridge workshop; honest yield below requested 50
Earlier proposal agents disappeared without saving files. Patrick asked about
status; main corrected the earlier unsupported running claim and restarted with
incremental saved batches. Three AI proposal lanes then saved88 attempts; main
added8, then a final bounded8-headword homonym batch, totaling104 attempts over
103 distinct terms/headwords (duct duplicated). Independent AI reviewer screened
all32 shortlist attempts:11 provisional admits,16 holds,5 rejects.
Other raw attempts were rejected by their proposal lanes,
not all independently re-adjudicated. No credentialed human expert is implied.

Added durable docs/sound-bridge-workshop.json plus a readable guide with all
103 terms, proposed cues, decisions, risks and limits. Only11 new candidates entered
the offline cue catalog:organ,palate,palm,rabies,wheal,corn,globe,crown,bridge,nail,
cone. They include2 constructed rebuses,2 homophones,7 homonyms; do NOT claim50
new sound bridges. Total catalog72 entries:54 candidates,17 legacy_unverified,
one restricted. Final homonym delta did not change earlier decisions.
Held/rejected ideas remain OUT of ordinary catalog search. No new medication
bridge survived this bounded review; that is not proof that none can be found.

Resources:local Tintinalli manifest topic tags and public ABEM EM Model for broad
curriculum orientation,not measured session frequency or PDF ingestion. Selected
NCI target pronunciations and Collins headwords were checked; not the whole bank.
Source verification does not establish cue recognition or learning effectiveness.
No proprietary mnemonic catalogs/scenes/characters imported; novelty unverified.

Full raw packet: Troubleshooting Prompts/sound_bridge_workshop_2026-10-19/.
No Anthropic/provider/image calls, no benchmark or learner trial; $6 cap untouched.
Nothing is automatically injected into Forge. Existing2 unrelated Forge edits
remain unstaged. Fetch still fails on the recorded Codex checkpoint-ref problem;
remote main was checked through authenticated GitHub API instead.
Final validation:catalog schema/path72 valid; focused104 passed,one skipped;
full suite736 passed,two skipped,149 subtests passed (48.13s). These checks prove
data/tool consistency only,not pronunciation accuracy,recall or image reliability.

### 2026-10-19 - Offline evidence-tagged cue catalog expansion
Patrick requested a larger cue bank with language/wordplay expert input.
Added docs/visual-cue-catalog.json (61 entries:43 candidates,17 unverified legacy,
one restricted), its readable guide, and a durable clock-hook failure summary.
Every entry has scope, exclusions, visible signature, collisions, provenance and
separate render/recall evidence. No entry has validated recall evidence.
The candidate catalog is OFFLINE ONLY and not automatically injected into Forge.

AI wordplay reviewer proposed24 entries (17 rejected,seven provisional); main
admitted only carpal,ataxia,rales,suture as untested sound bridges. A separate
36-item composition proposal set was screened, not bulk admitted. Independent
review caught false bicarbonate legacy attribution and branching/convergence
ambiguity; corrected both. No human specialist or clinical signoff is implied.
Public Sketchy/Picmonic/Pixorize descriptions informed general principles only;
no proprietary scenes,character systems or course catalogs imported.

Added tools/visual_cue_catalog.py with strict offline schema/reference validation
and bounded literal search. It rejects unsafe/missing/wrong-case local paths,
does not infer medical applicability, excludes restricted cues by default, and
always returns an unvalidated-design caveat. Validation is NOT evidence relevance.
Canonical tests run against a docs-only snapshot without ignored run artifacts.
Focused tests99 passed,one skipped (Windows symlink privileges); schema61 valid.
Final full suite731 passed,two skipped,149 subtests passed; tool compile passed.
No browser/provider/image/recall validation was performed for this catalog.

Raw proposals/rejections and review notes:
Troubleshooting Prompts/cue_catalog_2026-10-19/.
No Anthropic/provider/image calls made; future $6 benchmark cap untouched.
No new one-shot image or learning-effectiveness result is claimed. Next step is
small frozen candidate selection plus recognition/discrimination checks before
the separately budgeted first-pass trial, not unlimited library growth.
Pre-existing forge.html/cache and forge-pipeline.js/footer edits left unstaged.
Remote main was verified against local HEAD through authenticated GitHub API;
fetch still has the previously recorded unrelated checkpoint-ref problem.

### 2026-10-19 - Offline reset; $6 task-wide Anthropic pilot ceiling
Patrick rejected single-example perfection loops and approved a $6 TOTAL
Anthropic budget for a future bounded benchmark, not per topic or permission
to refill/retry. No new Anthropic calls made in this reset. Prior credit-balance
failure remains unresolved; no paid probe was used. Existing footer/cache edits
from the interrupted prior session remain uncommitted and unchanged here.

AGENTS.md and both Antigravity skill copies now require explicit shared budgets,
pre-dispatch reservations, frozen first-pass trials, no topic repairs/hook-reset
loopholes, and no automatic additional cohorts. This is operational policy,
NOT a claim that a runtime spending gate has been implemented.

Offline packet: Troubleshooting Prompts/offline_reset_2026-10-19/. PLAN.md records
the $6 approval, a proposed paired3-topic/6-render pilot, cost-envelope math,
required enforcement and stop rules. Candidate implementation, calibration,
guard tests, final freeze/topic draw and live benchmark are NOT complete.
A bounded independent agent compared saved79-vs100 disputes; rubric_findings.md
proposes prospective identity/relationship/viewing criteria without regrading
old images or changing the canonical rubric. Library review found scope ambiguity,
unsupported blanket proven/universal claims and manually duplicated catalogs.
library_findings.md proposes scoped evidence-tagged cue retrieval, not mass expansion.

Official standard/global Sonnet4.6 pricing was checked against Anthropic's pricing
documentation for planning ($3/M input,$15/M output); billing configuration and
final post-injection token bounds still require verification before any spend.
No Opus escalation is included in the proposed cost envelope. Codex-account and
Antigravity credits are distinct from the approved Anthropic dollars.

Git refresh encountered a bad refs/codex/turn-diffs/checkpoints object. Do not
delete unrelated Codex metadata or claim successful refresh without evidence.

### 2026-10-18 - Live full-scene development recoveries; no cold-run pass
**Done:** Pre-render critic now uses a forced strict tool response, with existing
local source-pair, quote, attribution and scope validation retained. Unsupported
read-only coverage contracts route to source-gap rather than invalid field edits.
Real provider compatibility required anyOf/scalar enums, not oneOf/object enums.
The image compiler no longer adds a fallback zone when an explicit scene location
occurs later in a VISUAL; scene terms exclude anatomical left/right contact.
Independent small-agent review added the ceiling case. VISUAL text is preserved.

**Verified:** 632 pytest passes/1 skip, compileall and four HTTP200 route checks.
An earlier focused run had one native Node access-violation exit, not an assertion
failure; isolated and full reruns passed. Three actual strict-review rebuilds
returned ready, but one later glaucoma review failed attribution and stayed blocked
until a successful new review. Schema validity is not semantic clearance.

**Actual image evidence:** Two frozen randomized cohorts remain terminal 0/6
end-to-end, blocked before images; do not relabel development recoveries as cold
passes. Expert recoveries produced full eight-unit images for esophageal rupture,
serotonin syndrome and acute angle-closure glaucoma. First stricter independent
scores: 71,93,55 respectively. Esophageal iteration2 scores70/70: lower barrel
missing and three backup prongs instead of two. Source/preflight readiness did not
predict a pass. Serotonin iteration2 is saved and being independently audited;
glaucoma's revised association/source checks cleared, with final concision pending.
Artifacts and true sources are under `Troubleshooting Prompts/fresh_cohort_2026-10-17/`
and `Troubleshooting Prompts/fresh_cohort_v2_2026-10-17/`. No final publication pass
or one-shot reliability claim exists at this checkpoint. Native JPEG bytes are
preserved even where target filenames end in .png. AG does not grade itself.

**Next:** Continue actual image iterations and source deltas to three strict
independent full-scene passes; retain every failure. Current esophageal recovery9,
serotonin recovery5/image iteration2, glaucoma recovery8 concision trial.

**Later same-session checkpoint:** Serotonin iteration2 independently100/100 PASS,
all8; first93 remains. Glaucoma iteration2 independently79/97, stricter79 REPAIR,
because completed through-opening is unidentifiable to the stricter reviewer.
Esophageal iteration3 independently55/55, missing target contacts and bubble
texture despite restored barrel/two flags. Actual next renders: esophageal4 from
recovery14, glaucoma3 from recovery12. Source delta clearances saved separately.
Esophageal's current user topic adds the source term perforation: a real new gate
then returns GI30/CV3. Captured diagnosis shows short-query GI30 still lexically
matches but fails both similarity/keyword-rank alternatives; no threshold relaxed.
This query change is development recovery, never a retroactive cold-run success.
Removed a duplicate compiler surfaceRule, leaving the complete final text fence
and every VISUAL unchanged; independent review found no unique constraint lost.
This avoids shortening load-bearing cues merely to meet prior repair budgets.

**Validation follow-up:** Default Node24.14/Python3.14 runs intermittently exited
with Windows0xC0000005, including one Python shutdown crash after all tests passed.
An independently checked process-local PATH selecting the already installed
Node24.19 completed632passes/1skip and all four HTTP200 smoke routes with exit0.
No assertion was suppressed or environment persisted. Root cause remains unknown;
local event logs also show unrelated native-process access violations. Targeted
builder/static-boundary suite101passes also exited0 on the default runtime.

**Image checkpoint:** Glaucoma iteration3 independently100/100 PASS, all8.
Esophageal iteration4 independently100/79; stricter79 REPAIR: central pump reads
as a plumbing fitting. Recovery15 targets this unit only for imageattempt5.
Passing topics so far: serotonin and glaucoma; one-shot success remains unproven.

### 2026-10-17 - Before/after preservation guard and independent live regression
**Done:** Changed targeted VISUAL patches now receive a separate strict-tool AI
comparison against the complete original/proposed lesson before returning. Exact
target/quote checks and original-word evidence coverage reject cherry-picked
positive inventories. Valid lost constraints block even with incomplete inventory;
the ledger marks that explicitly. No-op/clinical-only edits skip the added call.
Cancellation guards prevent stale follow-up calls and ledger delivery. Lost/invalid
semantic reviews do not enter the shorter-format retry loop. Original input remains
immutable. Current-quote-matching loss findings reach later scene repairs only as
advisory retention requirements, never clinical contract review or full redesign.

**Independent review:** Euler's partial-inventory finding and test gaps were fixed.
Hume implemented only disjoint offline tests, then hit a Codex usage limit. Euler
completed final code and exact semantic-delta audits: no unresolved material issue.
**Validation:** compileall,611pytestpasses/1skip, four HTTP200 route smoke checks,
real browser/provider repair/review exchanges and independent code/semantic audits.
No fresh-topic image or deployment-health claim follows from these checks.

**Live outcome:** Packet `Troubleshooting Prompts/preservation_2026-10-17/` retains
11 responses across four development trials (180058 input/6524 output tokens,
excluding retrieval/agents). Early malformed/overlength output failed closed.
The known historical lossy patch and a fresh default-model lossy patch were blocked.
One expert writer/reviewer pair preserved the original concrete relationships in
22/24/21-word fields; Euler independently verified the actual strings and exact
preservation of all other content. Semantic-equivalence guidance was clarified
after a reviewer overflagged a redundant intensifier. Expert draft stays unapproved:
no fresh medical gate/preflight/image was run; these are historical Forge-fixture
regressions, NOT new randomized-topic or first-image reliability evidence.

**Next:** Freeze the current pipeline for new full-topic first-image trials. Keep
default-model failures, expert recovery effort and stricter independent pixel
scores separate. The added AI comparison costs a request per changed-visual patch;
neither net cost savings nor semantic infallibility has been established.

### 2026-10-17 - Strict structured field repairs with independent checkpoints
**Done:** Replaced free-text JSON parsing in targeted field repair with one strict
custom tool response. Backend forwards tool_choice; pinned models unchanged.
Local validators enforce exact targets/status/keys, nonempty fields, explicit
redesign refusal and a VISUAL-only 24-word cap. Empty/duplicate targets fail before
paid work. Cache tag bumped. Independent Euler review caught a retry-classification
regression; fixed and covered through the actual helper and bounded preflight loop.
Final independent code review found no unresolved material issue.
**Validation:** compileall,589pytestpasses/1skip, four HTTP200 route smoke checks,
actual browser/provider structured checks, and independent semantic delta audits.
These checks do not establish fresh-topic image quality or deployment health.

**Live evidence:** Five provider calls total; two early tool responses lost full
artifacts to a harness URL-path bug, three subsequent calls fully captured under
`Troubleshooting Prompts/structured_repair_2026-10-17/`. Default/expert v29 checks
prove transport only (punctuation-only/no-op). A default v21 regression shortened
three existing Forge VISUALs from23/27/22 to18/20/18 words with other fields exact.
Hume independently verified outputs but found lost alcove-clearance/floor-support
constraints. That draft remains unapproved; no fresh gate/image was run. This is
NOT a new randomized topic trial or one-shot quality result.

**Next:** Spatial-constraint preservation remains an observed semantic risk; do
not equate schema success with safe compaction. Finish a prospectively frozen
fresh-topic cohort before making any first-image reliability claim.

### 2026-10-17 - Complete pericarditis image passes both independent audits
**Final outcome:** The second full eight-unit reference-conditioned image scored
100/PASS from both independent AI auditors under the unchanged canonical rubric.
All eight groups are identifiable at native and normal1024wide size; no hard gates.
Main verified pixels, hashes, category arithmetic and both per-unit ledgers. First
image remains75/75REPAIR. Source-qualified v29 story retained all clinical scope.

**Evidence:** Packet `Troubleshooting Prompts/pericarditis_production_2026-10-16/`;
`image_lab/fullscene_iter2.png`, `audit_iter2_A.md`, `audit_iter2_B.md`, source-review
reports, QA export and machine-checked `final_lesson_manifest.json`. Durable method,
results, limits and cost accounting: `docs/reference-conditioned-rendering-experiment.md`.

**Limits:** Three native image calls (one background/two full scenes), plus44captured
completed Anthropic responses across this packet's text/source/repair trials. Several
format/length failures and forensic draft restoration were required; this is NOT a
one-shot/default-model success or current-guideline certification. No renderer default
was changed. Generic treatment/ratio cues still require narration. The earlier layered
pilot remains89conservative; different content/effort prevents a superiority claim.

**Software:** Latest code has570pytestpasses/1skip, compile, route smoke, desktop/
mobile UI checks and independent static review. All app changes pushed onmain.
**Next:** Reduce structured-response/repair waste, then run a frozen fresh-topic
first-image cohort. Do not use another polished recovery as one-shot evidence.

### 2026-10-17 - Structured field-repair request and retained failed trials
**Done:** Field repair now serializes read-only lesson, selected targets and repair
instructions as structured JSON, with repair instructions last. Euler found no
actionable issue in the bounded delta. 570 tests / 1 skip, compile, smoke and both
UI viewports pass. This does not establish improved model concision: several live
field calls still failed local length/format requirements and were retained.

**Current recovery:** v29 cleared fresh source and preflight gates at 256 words /
1626 characters, versus the first full image prompt's 262 / 1670. All non-VISUAL
content is exactly source-approved v21; selected VISUALs2,4,5 are exact generated
text restored from a real format-failed Forge response. This is explicit forensic
draft recovery, not a successful default field call or held-out first-pass result.
The original strict-parser failure stays failed; no parser or rubric was weakened.
v27 was independently measured longer and NOT rendered, correcting main's earlier
informal estimate. Source/association delta review precedes the next full AG render.

### 2026-10-17 - Pixel feedback isolated from the clinical contract
**Done:** The full eight-unit v19 pericarditis scene rendered through AG's supported
native lane with the empty background as reference. Both independent audits scored
75/REPAIR: two bands contradicted the three-count cue; fluid-target/lens separation
also failed one auditor. Source approval did not conceal the pixel failure. A later
repair exposed raw visual/selected-unit feedback leaking into clinical contract
review. Contract review now receives only medical focus and prior clinical findings;
writer and whole-lesson critic retain full audit feedback and fresh source gates.
Pending failed clinical-patch findings now take precedence over older visual reviews
on retry. Constitution clarifies distinct inspectable targets and meaningful counts.

**Verified:** 570 pytest passes / 1 skip, compileall and all four route smoke checks.
Euler independently reviewed both new routing fixes. Failed v20 contract review was
blocked before the writer; v21 then completed a bounded source-grounded repair of
units2,4,5. A visual-only concision trial (v22) exceeded the original prompt-length
budget and was not rendered. Further budget-checked production field repair is v23.

**Limits:** First full hybrid render remains a failure, not one-shot success. No
second image score exists at this entry. Actual packets and independent reports are
under `Troubleshooting Prompts/pericarditis_production_2026-10-16/`. No renderer
default or rubric was relaxed. Continue through real Forge, QA export and full-image
independent audits; do not stop at the passing software tests.

### 2026-10-16 - Source-grounded recovery and preflight reliability
**Done:** Hardened current-topic/operation cancellation across live/demo generation,
micro-repair, rebuild and preflight; old completions cannot alter or unlock a newer
run. Source/scene findings require attributed current-field evidence. Preflight uses
the marked active Constitution contract, not the historical findings archive. Expert
recovery preserves source qualifiers, filters obsolete redesign context, and can
repair selected whole anchors with deterministic preservation of unselected units.
Review records join by unique anchor ID rather than provider array order. Resume-only
review accepts independent feedback without another full lesson rewrite.

**Verified:** Compileall, 568 pytest passes / 1 skip, and HTTP 200 smoke checks for
home, Forge, library and health. Desktop/mobile provider-free UI checks had no
overflow/errors, correctly blocked stale approvals, and sent zero paid requests.
Real expert Forge recovery v18 cleared all eight preflight rows with four matched
citations. Independent source review accepted the major association repairs but
found one remaining oral-anticoagulant qualifier missing in rapid review; v19 is
repairing that through the production source-grounded review/field-repair path.

**Known risks / NOT verified:** No new complete medical image has been generated in
this recovery yet. AG has generated an empty background only. Software tests,
lexical evidence matches, critic clearance and source approval are not pixel scores.
All packets are under `Troubleshooting Prompts/pericarditis_production_2026-10-16/`.
This is expert development recovery, not default-model or held-out one-shot evidence.

**Next:** Complete the source-qualified recovery, build its QA pack, render the full
eight-unit scene in AG using the native background reference, and independently
audit every anchor with the canonical rubric. Lower reviewer score governs.

### 2026-10-15 - Background and coordinate-layering comparison
**Done:** Patrick asked to test layered rendering against the existing whole-scene
image. Froze the real eight-anchor pericarditis v9 bundle. AG generated one background
and eight separate groups through the supported native chat lane. Two duplicate/corrupt
groups were regenerated separately (eleven native calls total). Deterministic local
compositing used masks, aspect-preserving placement, and a separately logged grounding
revision. No app defaults or medical content were changed for this experiment.

**Verified:** Two independent full-image/source audits: baseline 79/75, initial layered
75/79, final layered 89/96. Lower final score is 89 REPAIR, not a clean pass. Both found
all eight final cues versus seven baseline. Seven compositor tests passed; hashes prove
only two source assets changed and the background/six other assets were preserved.
All artifacts, original failures, revisions and audits are under
`Troubleshooting Prompts/layered_comparison_2026-10-15/`. Durable findings are in
`docs/layered-rendering-experiment.md`.

**Limits:** Native outputs were RGB PNG, requiring chroma-key cleanup. Shared camera,
support geometry and edge coherence were not guaranteed. One adaptive unequal-cost
trial does not prove reliability. Frozen source/association defects remain; the favorable
96 is pixel-only and does not approve the lesson. Auditor A corrected an earlier
baseline metaphor deduction; this is disclosed, not counted as a renderer improvement.

**Next:** Keep layering as an experimental targeted-repair route; validate common camera,
contact points and alpha on a source-approved fresh lesson before default integration.
Earlier app/preflight changes remain intentionally uncommitted, with unresolved review
findings around cancellation, scene-evidence attribution and harness termination. This
documentation commit does not claim those earlier changes complete. Main server stopped.

### 2026-10-15 - GitHub CLI route verified; interrupted review work preserved
**GitHub:** Patrick supplied the current shared sync runbook and pointed to
Transform_clean. Verified `Pulpers859` CLI/keyring authentication and the configured
GitHub credential helper. Direct fetch succeeded; main was ahead by one with a
shared ancestor. Pushed `9da785e` without force, verified exact remote SHA
`9da785e67cf15005dbd7aff00d9a197546946c09`, and verified the previous remote
`5dd95fc` remains an ancestor. Updated repo instructions and both handoff skills:
GitHub Desktop is optional, not a prerequisite. No credentials/config were changed.

**Prompt work is NOT complete:** Newer active-Constitution, repair-context and
review-routing edits remain intentionally uncommitted pending integration and final
validation. Earlier validation reached 419 passes/one skip and route/UI smoke;
later cancellation edits still need regression coverage. The independent reviewer
also found optional repair scopes and duplicate lesson context; its follow-up worker
became unavailable across the interruption, so do not assume that patch landed.
No new image or passing image score is claimed.

**Recovery evidence:** Paid Anthropic calls resumed after refill. v5/v6 pericarditis
recoveries failed pre-render review; v6 exposed unsupported collision findings and
cue substitutions inconsistent with learning text. v7 reached review round 2 before
interruption. Its current bundle is 58,455 zero bytes, so its final outcome cannot
be verified or reused. v4/v6 bundles remain readable. Preserve the bad packet for
diagnosis; do not call it a pass or reconstruct clinical content by hand. Earlier
frozen failed cohorts remain unchanged. Next integrate the bounded reviewer fixes,
add cancellation coverage, revalidate, then resume the actual Forge workflow.

### 2026-10-15 - One-shot infrastructure and failed prospective pilot
**Done:** Added source-grounded whole-lesson pre-render review, one bounded clinical
correction before locking clinical text, at most two visual repair requests,
deterministic compilation of reviewed opening/VISUALs, exact story/prompt binding,
and a single full-scene image request. Added private review/repair export, an
explicit reviewed redesign path, and frozen first-pass evaluation with two-auditor
artifact hashes. Old pixel-prompt injection cannot bypass preflight. Fixed the
retrieval relevance filter treating learner/output prose as medical topic terms.
Protected asynchronous gate, repair and image results against newer lessons.

**Actual trials:** Original frozen cohort0/3 (compartment syndrome, acetaminophen
poisoning, myasthenic crisis); follow-up0/1 (pericarditis). All blocked before images.
The first two completed scenes exceeded critic output budgets; acetaminophen lacked
specific retrieved toxicology support. Pericarditis exposed a relevance-filter bug:
identical saved retrieval rows retained1 before and5 after the correction. Recovery
cleared clinical coverage but exhausted visual repair with unresolved critic
objections. Some objections were demonstrably wrong; critic instructions now clarify
object counting, mnemonic names and the actual compiler boundary. No false-positive
elimination or one-shot reliability is claimed.

**Current blocker:** A full Forge redesign produced eight anchors and passed the
medical gate with four citations, then Anthropic returned HTTP400, credit balance
too low. Patrick was notified; no further paid retries. Resume gate/preflight from
`Troubleshooting Prompts/first_pass_2026-10-15/pericarditis_redesign_v4/03_forge_bundle.json`
after refill, without discarding original failures or counting recovery as held-out.
No new image was generated in this session. Previous nine-render CO pass remains
development evidence only.

**Validation:** Compileall, 387 tests passed (one Windows symlink skip), all four
route smoke checks, and provider-free desktop/mobile UI checks passed. JavaScript
syntax checks and diff whitespace checks passed. Real Forge/Anthropic/retrieval
calls exercised the failures above. No Antigravity/image call was appropriate without
clearance. Independent code and accounting reviewers identified and checked risks.

**Next highest-value step:** Calibrate the pre-render critic against exact supporting
quotes and actual images, then run a new prospectively frozen cohort after the final
pipeline version is fixed. Do not increase rejection/retry count and call it quality.
See `docs/visual-preflight.md`, `docs/first-pass-evaluation.md`, Constitution findings
38-39, and the private pilot `RUN.md` for scope, provenance and caveats.

### 2026-10-15 - Full CO lesson passes independent whole-image audits
**Done:** Completed the preceding Forge-first student trial through nine actual
Antigravity native image renders. Final image 9 scored 100 in each of two independent
canonical pixel audits, with 8/8 teaching units and no hard gates. No subset plates,
hand-authored medical scenes, or renderer self-grading. Rejected all prior images;
used the stricter decision when reviewers disagreed. Changed failed source-check
encoding prospectively through Forge to a conditional source-restriction/calendar
cue while preserving all clinical clauses, facts and reviewed coverage.

**App changes:** Targeted repairs can update explicitly selected visuals and now
validate their image renderability before returning. Source-required names retain
their exception to unmarked-surface rules; text-free lessons explicitly request
unmarked clothing/devices. Architecture is concise, full visual fields survive,
and explicit Indoors/Outdoors placement no longer gains a conflicting default zone.
Cache versions and nonclinical regression tests updated. Constitution records actual
pixel failures, cross-anchor regression, prospective redesign and reference risk.

**Verified:** compileall, 133 pytest tests, JS syntax and four HTTP 200 route smoke
checks. Independent code review's two findings were fixed and tested. Final study
page passes 1440px desktop and 390px mobile checks: eight sections, image loaded,
no horizontal/text overflow or page errors. All private artifacts remain ignored
under `Troubleshooting Prompts/co_student_2026-10-14/`: final/study.html,
final/03_forge_bundle.json, final/verification.json, antigravity_iter9.png,
antigravity_audit_iter9_a.md and _b.md. Image SHA256 starts 18d70f98e677b711.
The promotion script verifies both scores, arithmetic, full coverage and matching
image hashes before embedding the image in the exact reviewed Forge bundle.

**Limits:** This is one source-bounded Tintinalli introductory lesson, not licensed
clinician certification, a current-guideline protocol, or proof of general one-shot
reliability. Extra sample/table-placement deviations do not trigger rubric deductions
and are disclosed in the audits. Gemini API text-director credits returned 402;
Claude fallback and expert repairs were used, while Antigravity generated the images.
The native image quota reset caused an approximately four-hour wait. Render 8's
reference-guided repair failed; render 9 passed fresh with the same prompt. Nine
renders, not one. Private source excerpts/images were not staged for GitHub.

**Next highest-value step:** Evaluate the current source-reviewed pipeline on fresh
full lessons with prospectively fixed contracts and strict independent audits;
measure first-pass success and repair regression instead of extrapolating from one
passing artifact. No further image work is required to complete this one-topic task.

---

### 2026-10-14 - Full CO student lesson: clinical clearance, image quota wait
**Prepared:** A fresh Forge-first carbon-monoxide introduction with all eight teaching
units, independently reviewed against retrieved Tintinalli pages 83-85. Rejected
multiple drafts rather than accepting the lexical gate's apparent pass. Fixed source
excerpt truncation, silent incomplete planning, independent source review of the
coverage contract, compact-first writing, complete nontruncated image prompts,
repair schema/preservation, stale visible prompts, and error recovery. Added optional
expert/redesign repair and narrowly targeted clinical-text repair functions.

**Verified:** compileall, 130 pytest tests, and HTTP 200 smoke for `/`, `/forge`,
`/library`, `/api/health`. Real source retrieval and Anthropic generation/repairs ran.
The final eight-unit lesson passed independent source review; exact image prompt,
narrations, contract, evidence and failed trials are saved under
`Troubleshooting Prompts/co_student_2026-10-14/`. The final bundle is
`final/03_forge_bundle.json`; its visuals are unchanged from the submitted image prompt.

**Not yet verified:** NO image or image score. Antigravity's native image tool returned
429 with reset `2026-10-15T05:03:46Z`; the task remains active awaiting that reset.
Gemini API text-director credits also returned 402, so Claude fallback composed the
image prompt. This is a scoped textbook lesson, not a comprehensive current-guideline
protocol. Default Sonnet one-shot clinical/visual reliability is NOT established.
The unchanged legacy demo now reports its invalid precision-text prompt safely instead
of leaving the Forge button disabled; its medical content was not hand-rewritten.

**Next:** Resume the saved Antigravity chat/image task after quota reset, independently
inspect/score all eight anchors under the canonical rubric, repair through Forge as
needed, and record the actual final result. Do not reuse older three-anchor plates or
call this task complete based on source/software checks alone.

---

### 2026-10-14 — Source-grounded random EM visual loop + precision-device hardening
**Done (this commit):** Ran three new random topics through the real Forge browser
pipeline, captured the structured medical quality-gate exchanges, exported Forge
bundles, built QA packs, rendered focused plates through the supported Antigravity
chat/image lane, and externally audited every image against the canonical rubric.
Hardened the quality gate so generated concepts must also be independently grounded
by topic-relevant citations; broad cross-topic citations no longer satisfy the gate.
Added controlled Supabase transport errors, browser-harness gate capture, the missing
numeric-text rubric deduction, and a production rule that replaces exact-value
clocks/dials/gauges with physical thresholds, size contrast, or small countable sets.

**Verified:** Final external scores were SBP 100/100 after three renders, heat stroke
100/100 on the first improved-contract render, and pediatric intussusception 100/100
on the first improved-contract render. All source bundles, citations, prompts, images,
and audits are under `Troubleshooting Prompts/random_em_2026-10-14/`; each grounded
run includes a post-fix `07_quality_gate_recheck.json`. Supabase source retrieval was
restored and returned direct Tintinalli topic evidence for all three runs, with zero
missing or ungrounded required concepts. Full local validation passed: compileall,
89 pytest tests, and HTTP 200 smoke
checks for `/`, `/forge`, `/library`, and `/api/health`.

**Known risks / NOT verified:** Final images are focused plates using Forge anchors
1-3, not full 10-anchor scene renders. The raw roughly 1,000-word Stage-3 fallback
prompt scored 71 on its first SBP render; the concise all-visual contract, not the raw
fallback, produced the one-shot 100s. Gemini text-director credits returned 402 during
the run, so the production Claude fallback built the prompts. Source coverage labels
remain conservative (`partial` for a strong exact lexical match unless multiple high-
similarity chunks support `strong`). Antigravity did not grade its own output.

**Next highest-value step:** Make the concise 1-3-anchor all-visual plate builder a
first-class Forge output mode, then repeat this trial on full-scene output and denser
numeric algorithms before claiming one-shot reliability for all scene sizes.

---

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
