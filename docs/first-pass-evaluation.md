# Offline First-Pass Evaluation

`tools/first_pass_evaluation.py` is a standard-library-only evaluation ledger. It
does not generate medical content, render images, call providers, load credentials,
import the backend, or run Git. All cohort files, exports, images, audits, receipts,
SQLite ledgers and redirected reports must live under `Troubleshooting Prompts/`.
Tests use temporary synthetic repositories instead.

## Freeze Before Generation

Finish production edits first. Freeze the cohort **before any topic is submitted
to Forge**, not merely before image rendering. Never replace a failed topic, shorten
its scope to a successful subset, or reuse a prior image as a prospective result.

The production fingerprint covers `frontend/pages/forge.html`, every JavaScript
file recursively under `frontend/scripts/`, and every Python file recursively under
`backend/app/`. That includes the new `forge-visual-preflight.js`, pipeline, auth,
and backend main changes. Paths and byte hashes are sorted into a SHA-256 manifest.
Added or removed files also change it. Rubric and Constitution byte hashes are
recorded separately. Documentation, tests, this CLI and other offline tools are
excluded from the **production** fingerprint. Changing the rubric or Constitution
still prevents subsequent registration/render recording for that frozen cohort.
Configuration, provider versions, remote behavior and secrets are NOT fingerprinted.
Pin provider/model settings operationally and record them in the cohort metadata.

Create the cohort JSON in the run directory using this schema. The prompts below
are an example cohort chosen by the main agent. Replace the novelty placeholders
with a real review basis, supply all known prior full topic prompts, and set actual
auditor/generator identities **before** freezing. An empty history is a claim about
the reviewed history, not proof that a topic is novel.

```json
{
  "before_any_generation": true,
  "generator": "actual-image-generator-model-or-review-principal",
  "auditors": ["actual-independent-reviewer-one", "actual-independent-reviewer-two"],
  "novelty_review": "REPLACE: inventory reviewed, reviewer, date, and selection method",
  "prior_topic_prompts": [],
  "topics": [
    {
      "id": "compartment",
      "expected_anchor_count": 8,
      "prompt": "Acute compartment syndrome: an introductory emergency medicine lesson for a medical student, eight anchors.",
      "novel": true,
      "full_topic": true,
      "novelty_basis": "REPLACE: why this full topic is novel against reviewed history"
    },
    {
      "id": "acetaminophen",
      "expected_anchor_count": 8,
      "prompt": "Acetaminophen poisoning: an introductory emergency medicine lesson for a medical student, eight anchors.",
      "novel": true,
      "full_topic": true,
      "novelty_basis": "REPLACE: why this full topic is novel against reviewed history"
    },
    {
      "id": "myasthenic",
      "expected_anchor_count": 8,
      "prompt": "Myasthenic crisis: an introductory emergency medicine lesson for a medical student, eight anchors.",
      "novel": true,
      "full_topic": true,
      "novelty_basis": "REPLACE: why this full topic is novel against reviewed history"
    }
  ]
}
```

From `C:\Dev\Mnemorized`, in PowerShell:

```powershell
$run = 'Troubleshooting Prompts/first-pass-pilot'
$ledger = "$run/ledger.sqlite3"
python -B tools/first_pass_evaluation.py --ledger $ledger freeze --cohort "$run/cohort.json"
python -B tools/first_pass_evaluation.py --ledger $ledger report
```

The freeze command refuses to replace an existing file. It returns the production,
rubric and Constitution hashes and the three-topic denominator. Keep its event-head
hash as an independently witnessed checkpoint if stronger provenance is needed.
New pipeline versions require a new prospective cohort, not a thaw or rerun of
these now-exposed topics. Do not discard the old cohort from aggregate reporting.

## Register Before Rendering

Run the frozen full prompt through the real Forge pipeline. Export its full bundle
and the exact UTF-8 `image_prompts.prompt2` text **before rendering anything**.
No prompt shortening, rebuilding via offline QA tools, or selecting anchor subsets.
This protocol evaluates a single full-scene render of prompt2; a preceding generated
room image is already a render and must not be silently omitted. Exported generated
image fields must be empty. A UTF-8 BOM on the prompt file is accepted; its raw byte
hash remains distinct from the preflight's UTF-8 text hash.

```powershell
python -B tools/first_pass_evaluation.py --ledger $ledger register --topic compartment --bundle "$run/compartment/bundle.json" --prompt "$run/compartment/prompt.txt" --before-render
```

Registration requires a v1 Forge bundle whose `topic` exactly equals the frozen
input, nonempty unique integer anchor IDs, and the exact exported prompt2. It enforces
the optional prospectively frozen `expected_anchor_count` (eight for each example
pilot topic), without inferring counts from natural-language text. It stores the
original bundle and prompt bytes, not references to mutable files. It validates:

- `quality_gate_data.verdict == "ready_for_review"`, `evidence_status == "matched"`,
  nonempty evidence, and explicit empty `missing_from_generation` and
  `ungrounded_concepts` arrays.
- Nonempty `story.required_concepts` and `visual_preflight.version` of
  `visual-preflight-v1` or `visual-preflight-v2`, with status `ready` or `blocked`.
- Ready preflight's story/prompt SHA-256 bindings, clinical preservation attestation,
  zero through two repairs, contiguous review rounds and corresponding story hashes.
- Supported clinical disposition with no clinical findings on every round; final
  anchor rows ready, with no risks, exact relationship quotes from VISUAL, source
  references drawn from the supplied evidence, and a ready scene with no issues.

### V2 Clinical Repair History

V1 remains supported with its existing visual-only protocol. V2 adds at most one
source-grounded clinical repair **before** clinical text is locked for the zero to
two visual-only repair rounds. It does not replace medical evidence clearance or
either independent pixel audit. Ready v2 exports additionally require:

- `original_story_sha256`: the story before any clinical repair.
- `input_story_sha256`: the story after clinical repair, also the hash of the first
  complete visual review attempt. With no clinical repair, it equals the original.
- `clinical_repair_count`: an integer 0 or 1, not a boolean; `clinical_attempts`
  must have exactly that many entries.
- `visual_repair_requests`: an integer 0 through 2 for **all** visual repair
  requests, including rejected patches. `repair_failures` records each rejected
  validation request as `{ "request": 1, "error": "nonempty actual error" }`.
  Request numbers are unique, strictly increasing, one-based, and within the budget.
  For a ready report, requests must equal applied `repair_count` plus the number of
  failures, and the last request cannot be a failure. There is no extra retry budget.
- Each clinical attempt has a `review` with `clinical_status: "needs_repair"`,
  nonempty structured `clinical_findings`, `before_sha256`, `after_sha256`, and a
  `repairs` list. `source_gap` is never repair permission.
- Findings identify `n`, `field`, a nonempty `issue`, and nonempty `source_refs`
  matching retrieved evidence by `source_key` and integer `page_start`. Allowed
  targets are an existing anchor's `anchor` or `narration`, or `n: null` with
  top-level `review_script`. VISUAL, hook, opening, coverage contract and other
  fields are forbidden in this clinical patch.
- Repairs contain exactly `anchor`, `field`, `before`, `after`. Every distinct
  finding target must have exactly one patch, with nonempty text values. Extra,
  unknown, duplicate or unselected patch targets are rejected.

The ledger reconstructs each earlier story from the final export, reversing the
recorded visual-only edits first, then the permitted clinical edits. Every boundary
must match its recorded hash; the clinical before/after hashes must equal original/
input respectively. This detects omitted or unselected field changes without
generating any content. All v2 visual attempts, including the complete rereview
immediately after clinical repair, must have supported clinical status, no clinical
findings, and complete anchor/source/scene review rows. Earlier visual repair rows
must identify the exact targets changed; the final review must be fully ready.
Missing history, a forged preservation flag alone, or partial rereview cannot pass.
Deterministic `signals.risks` marked `blocking: true` also select repair targets,
even when the critic's anchor row says ready. Every supported attempt must retain
its structural signals with no errors; the final attempt must have no blocking
signals. Failed patch validation consumes a request without changing the story or
adding a review round: `attempts.length == repair_count + 1` still holds.

An early clinical failure may omit visual rows because it has not approved the
lesson. That applies only to the initial `needs_repair` finding, never to the
post-repair supported rereview. Blocked exports can retain incomplete diagnostics
but remain blocked; their incomplete repair history is not certified as successful.
Older registered v1 records need no migration and report zero clinical repairs.
New records expose `preflight_version`, `clinical_repair_count`, and the existing
`preflight_repair_count` (applied visual repairs) separately, plus
`visual_repair_requests` and `repair_failure_count`. V1 request counts are unknown
(null), not retrospectively invented. A blocked v2 export may have a request that
failed for another reason before an applied patch or validation-failure receipt;
it remains blocked and never qualifies for a pass.

Source citations are checked against the evidence retained in the export. If a
clinical recheck changes the retrieved evidence set and loses an earlier cited
source, registration fails closed; preserve the needed evidence through the Forge
export, rather than weakening reference checks. Hash integrity and citation membership
are provenance checks, not proof of medical truth or source entailment.

The story binding reproduces compact UTF-8 JSON of `{topic, story}` in exported key
order, matching ordinary string/integer Forge payloads. Exotic JS numeric
serialization can differ from Python JSON; a mismatch blocks rather than relaxing
the binding. This checks receipt structure, NOT clinical entailment or source truth.
The full frozen request and exported anchor inventory remain available for review;
the CLI does not infer whether every learner requirement was actually fulfilled.

A registered `blocked` preflight cannot render. If export/preflight fails before a
registerable bundle exists, retain the topic with a terminal blocked event:

```powershell
python -B tools/first_pass_evaluation.py --ledger $ledger blocked --topic compartment --reason 'Forge stopped before export: record the actual gate failure here'
```

An integration may additionally supply `--preflight receipt.json`. That receipt must
contain `status` (`PASS` or `BLOCKED`, agreeing with the bundle), `reason`,
`full_scene: true`, `before_render: true`, `bundle_sha256`, `prompt_sha256`,
`topic_sha256` (UTF-8 frozen input), and `pipeline_sha256`. It supplements the
structured bundle checks; it cannot override them. Without a receipt,
`--before-render` supplies the registration-time attestation.

## Lock The First Image

Immediately record the **first actual image returned**, before looking for a better
candidate. `--first-render` is an explicit operator attestation. Source drift since
freeze blocks recording, so keep production files fixed during the pilot.

```powershell
python -B tools/first_pass_evaluation.py --ledger $ledger first-image --topic compartment --image "$run/compartment/first.png" --first-render
```

No overwrite, reset, unfreeze, replacement audit, or delete command exists.
Registration and first-image selection are each one-shot. SQLite transactions
serialize competing writers, and triggers reject SQL UPDATE/DELETE. The ledger
retains the actual artifact bytes plus SHA-256 and chains timestamped event hashes.
Image bytes are treated as opaque: this tool does not decode pixels or certify that
a file contains a real render. Independent auditors must actually open it.

Record failures and later images separately; they never become the primary image:

```powershell
python -B tools/first_pass_evaluation.py --ledger $ledger attempt --topic compartment --attempt-kind render_failed --reason 'Actual error; no image returned'
python -B tools/first_pass_evaluation.py --ledger $ledger attempt --topic compartment --attempt-kind repaired --reason 'Actual repair reason' --image "$run/compartment/repaired.png" --prompt "$run/compartment/repair-prompt.txt"
```

`additional` is also available for later non-repair images. Later images require
an already locked first image and their own prompt. Their scores cannot enter
first-pass results. First-image audits only are supported by this lean ledger;
save secondary audit packets separately under the same run directory.

## Two Independent Audits

Preassign two genuinely independent external reviewers, neither the image generator.
They must inspect the same first-image bytes without seeing each other's assessment.
Use actual reviewer/model identities, not two aliases for the same review process.
Each identity has exactly one immutable audit slot per topic. A malformed submission
is retained, consumes that slot, and prevents a pass; do not shop for a third grade.

Each audit file is a UTF-8 JSON envelope with these fields:

```json
{
  "auditor": "actual-independent-reviewer-one",
  "image_sha256": "first-image SHA-256 from report",
  "rubric_sha256": "frozen rubric SHA-256 from report",
  "constitution_sha256": "frozen Constitution SHA-256 from report",
  "viewed_image": true,
  "independent": true,
  "consulted_other_audit": false,
  "canonical_audit": "The exact nine-line plain-text canonical audit block, encoded as a JSON string",
  "anchor_evidence": [
    {"anchor": 1, "status": "present", "location": "specific pixel location", "observation": "specific observed shape or relationship"}
  ]
}
```

Supply one evidence row for **every** exported anchor, not just the example row.
Use `absent` for missing/unidentifiable anchors, with a searched location and honest
absence observation. Use the nine-line format in `docs/image-scoring-rubric.md`:
`OVERALL_SCORE`, `DECISION`, `CATEGORY_SCORES`, `RAW_SUM`, `GATES_TRIGGERED`,
`ANCHORS_PRESENT`, `MISSING_ANCHORS`, `TOP_ISSUES`, `REPAIR`, in that order.
Gates use `none`, `G1(1 missing) cap79`, or semicolon-separated tokens such as
`G2 cap88; G6 cap90`. No Markdown fences, missing fields, duplicate keys,
unknown gates, fabricated caps, non-integer scores, or score-only fallback.

```powershell
python -B tools/first_pass_evaluation.py --ledger $ledger audit --topic compartment --auditor actual-independent-reviewer-one --audit "$run/compartment/audit-one.json"
python -B tools/first_pass_evaluation.py --ledger $ledger audit --topic compartment --auditor actual-independent-reviewer-two --audit "$run/compartment/audit-two.json"
python -B tools/first_pass_evaluation.py --ledger $ledger report
```

The parser enforces category ranges, sums, mandatory missing-anchor deductions,
gate-implied deductions/caps, anchor denominators/IDs, image and contract hashes,
and decisions no more permissive than the arithmetic. A stricter reviewer decision
(e.g. strategy-level REGENERATE) is preserved. Between valid audits, the lowest
score, strictest decision and union of gates govern. No averaging or best-of-N.
Partial scores from one valid audit can be displayed, but cannot produce a pass.
Submission success means evidence was recorded; inspect `audit_errors` and status
in the JSON result to learn whether that evidence is valid.

## Reporting And Limits

- `cohort_denominator`: every frozen topic, permanently including blocked, absent,
  unrendered, malformed-audit and incomplete-audit outcomes.
- `first_render`: two-audit PASS count divided by topics with a locked first image.
  Unreviewed images stay in this denominator. No images gives a null rate, not 100%.
- `first_render_cohort`: the same image-pass numerator over the entire cohort.
- `end_to_end`: valid first-image PASS plus cleared structured preflight, no terminal
  block, and no recorded failed render before the first image, over the entire cohort.
  This is not an eventual-pass-after-image-repairs metric. Bounded **pre-render**
  repairs inside the frozen production pipeline are allowed: zero to two visual
  repairs for v1/v2, and at most one earlier clinical repair for v2. Both counts
  are reported explicitly; this is not a zero-text-retry metric. Later image attempts
  do not improve or degrade the locked first-render outcome.

Novelty checking is a **heuristic**: Unicode NFKC, case folding and whitespace
normalization detect exact normalized duplicates within the cohort and against the
supplied history. They do not detect related topics, paraphrases, hidden prior runs,
or changes in topic difficulty. Full-topic coverage, honest registration chronology,
actual pixel inspection, source truth, reviewer identity and independence require
external evidence and honest attestations. Nonempty prose is not evidence validation.
The CLI never claims to establish medical correctness from receipt structure.

Immutability is within this CLI and its SQLite schema, **not physically irreversible
storage**. A file owner can replace a database, drop triggers, rewrite all hashes,
truncate an unwitnessed suffix, forge timestamps or omit external attempts. Preserve
independently witnessed freeze/head hashes and an external run log for stronger
assurance. Do not edit this CLI's grading policy mid-cohort; production hashing
intentionally excludes the evaluation tooling itself.

Three topics are a descriptive pilot, **not a reliability estimate or certification**.
Even 3/3 does not establish general one-shot reliability. Report failures and missing
outcomes, selection method, pre-render repair counts, audit disagreements, model/settings
and protocol deviations. Do not pool cohorts with different production/contract hashes
without clearly separating versions. No provider or browser testing is performed here.

### Original Pilot Remains 0/3

The baseline cohort at `Troubleshooting Prompts/first_pass_2026-10-15/pilot.sqlite3`
is terminally blocked for all three frozen topics: two preflight responses truncated
at 5,000 output tokens and one source-coverage gap. Its frozen production fingerprint
is `60e91d8500e08c108cae5cc8c29e210ebb8af7c350020d1f04b682292b01b372`.
The end-to-end result remains **0/3**. There were no locked first images, so the
conditional first-render metric is 0/0 with a null rate, not an image-quality score.

V2 does not reopen or migrate those outcomes, replace the denominator, or relabel
those exposed topics as novel. New prospective v2 results require a separate frozen
cohort and production fingerprint; rerunning the original topics is diagnostic work,
not a replacement first-pass result. Reports use read-only SQLite connections and
do not update the original ledger. Preserve the baseline alongside any later cohort.

## Offline Tests

### 2026-10-17 Prospective Cohort: 0/3 Before Rendering

The frozen cohort at `Troubleshooting Prompts/fresh_cohort_2026-10-17/ledger.sqlite3`
selected esophageal rupture, acute bacterial meningitis and neuroleptic malignant
syndrome from a recorded randomized pool after reviewing saved topic history.
Fingerprint `70a76da17314e3615639d7aac8b7355d0a5a910007183e823b1b91596b380061`.
All three remain terminally blocked, end-to-end0/3, no images and a null conditional
first-image rate. Esophageal rupture exhausted bounded visual repair; meningitis
returned corrected units plus a gap for a removed claim; NMS retrieved an incidental
mention instead of an already-ingested detailed passage. No rubric was changed.

Focused-query diagnostics found the NMS section in psychosocial page23. A narrow
retrieval fix removes only a complete trailing app-format lesson suffix from both
embedding and hybrid search queries, leaving clinical requirements intact. Contract
instructions now distinguish resolved corrections from remaining unsupported scope;
the parser still blocks every returned source_gap. These changes require a new
prospective cohort. Exposed-topic expert recoveries remain diagnostic, not replacements.

```powershell
python -B -m unittest discover -s tests -p test_first_pass_evaluation.py -v
```

Fixtures contain only synthetic nonmedical content. Tests cover malformed/inflated
audits, gate arithmetic, disagreement, missing evidence, frozen denominators, source
drift, tampering, replacement attempts, path confinement and concurrent first writes.
