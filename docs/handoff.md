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
