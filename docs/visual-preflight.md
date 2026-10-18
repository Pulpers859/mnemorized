# Pre-Render Visual Review

Forge's objective is one source-grounded, publishable full-scene image on the
first render. Pre-render text review and bounded text repair are allowed; a
second image is not a first-pass success. Neither a prompt review nor a software
test establishes pixel quality, clinical certification, or learner retention.

## Production Path

1. Forge generates an independent clinical coverage contract and a complete lesson.
2. The medical retrieval/coverage gate must return `matched`, `ready_for_review`,
   citations, and no missing or ungrounded concepts. This is lexical coverage,
   not clinical entailment.
3. `forge-visual-preflight.js` calls a separate source-grounded critic. The backend
   injects the Constitution's marked ACTIVE PRE-RENDER CONTRACT and bounded private
   source excerpts. Missing, empty, or ambiguous contract markers fail closed before
   a provider call. Historical renderer notes are not additional pre-render rejection
   rules; the complete canonical pixel rubric still governs independent image audits. The
   critic checks all clinical text, the narration-to-visual associations, every
   required visual relationship, and the whole scene's physical conflicts.
4. Deterministic validation requires every stable anchor ID exactly once,
   verbatim relationship spans, retrieved source references, explicit dispositions,
   and consistent risk/clearance fields. Repair scopes and scene issue fields are
   mandatory; scene findings must quote the exact attributed lesson fields and
   support their affected anchors. These checks validate the review contract;
   they do not make the critic's semantic judgment infallible.
   A review-script quote can support a whole-lesson association finding, but cannot
   waive attributed anchor evidence for a visual-layout or opening finding.
5. One targeted source-grounded clinical correction may run before visual text is
   locked, limited to specifically cited anchor/narration/review-script fields.
   It must pass the medical gate and critic again. Source gaps still block.
   Then at most two visual-only repair requests run, including rejected patches,
   followed by fresh whole-lesson review. HOOK, clinical text, review script and
   required scope remain identical throughout visual repair. A new association
   requires explicit Forge redesign, not an unreviewed visual patch.
   The patch writer receives the complete lesson as read-only context, including
   HOOK and review script, and can reject a request that requires new cue identities.
   Opening and association defects route directly to redesign rather than consuming
   the visual-only patch budget. Exact quote validation applies to repair findings
   as well as ready rows; it does not prove the critic interpreted those words correctly.
   Format-only repairs also retain the original topic and operation identity;
   superseded responses cannot initiate another paid repair against a new topic.
6. The compiler concatenates the reviewed architecture, every complete VISUAL,
   fixed style constraints, and the exact text allowlist. It does not commission
   a second provider to paraphrase approved relationships. Oversize output fails
   rather than silently truncating an anchor.
7. Review is bound to the topic, complete story/contract and both exact prompts.
   Missing/stale approval blocks both native API rendering and Antigravity handoff.
   Restored lessons need fresh review before a new render. The render action sends
   only the full-scene prompt; the empty-room prompt is an optional export.

## Evidence And Limits

Bundles and private saves include `quality_gate_data` (bundle) / `quality_gate`
(save), plus `visual_preflight`, its attempt ledger, exact relationship quotes,
source references, repair diffs, and source/prompt hashes. Blocked draft exports
remain available and must not be counted as publishable results.

Exact quote membership proves an instruction exists, not that an image model will
follow it. Source-reference membership proves attribution is in the retrieved set,
not clinical entailment. Semantic judgments are AI review, not physician review.
Crowding, repeated props and preparatory verbs are evidence-informed risk signals,
not calibrated predictive thresholds. No pre-render percentage is assigned.

Post-render review remains independent under `docs/image-scoring-rubric.md`.
Legacy image-audit prompt injection cannot reuse stale preflight approval: failed
images return to Forge's reviewed repair path. First-pass evaluation uses frozen
cohorts and first-artifact hashes; eventual best scores are reported separately.

A blocked preflight exposes an evidence-backed redesign action alongside the
medical gate without changing the gate's evidence verdict. Critic feedback is
advisory input to redesign, not a source of medical truth. Redesign requires a
new gate and preflight and is a recovery, not a fresh held-out first-pass result.
The critic is told which fields actually reach the image compiler, to count all
explicit objects, and not to confuse historical risk patterns with observed
pixel defects. These instructions are not evidence that false positives are
eliminated.

Expert recovery explicitly selects the configured advisor model for the writer,
critic and bounded field repairs. Ordinary generation keeps its default model;
expert outcomes must not be presented as proof of default-model reliability.
The recovery harness supports `--redesign` or `--repair`, `--expert-review`, and
`--feedback-file` for an independent audit. Feedback is limited to 20,000 characters,
treated as unapproved observations, and recorded with its SHA-256 in recovery
provenance. Saved review history and prior patches are advisory context only,
never imported clearance. Every recovery still runs the medical gate and preflight.
Resume-only review/rebuild accepts expert review and external feedback without
commissioning another lesson rewrite. Anchor review records are joined by explicit
ID, with exact-once coverage required, rather than depending on response order.
Clinical repair findings must quote the current target field exactly (at least four
words, or the complete field if shorter); historical audit quotes cannot authorize
a repair against a revised lesson. These checks establish attribution, not entailment.
Clinical contract re-review receives only medical gate focus and prior clinical
findings, never selected-visual-unit instructions or raw external layout feedback.
The scene writer and whole-lesson critic still receive the full independent audit;
source findings are checked there against the newly reviewed complete contract.
Targeted field repair sends structured read-only lesson context, then selected
targets, then repair instructions. This ordering and field-only application are
tested; observed concision reliability is not established by those tests.
Targeted field repair now requests a single strict `submit_field_repairs` tool
response instead of parsing prose as JSON. The proxy forwards `tool_choice`.
Local validation still enforces exact ordered target indices, allowed keys,
nonempty replacements, explicit redesign refusal, and a 24-word limit on VISUAL
only. Invalid output never mutates the input lesson. Overlength patches enter
the existing bounded format-retry budget, not an unbounded retry or truncation.
No free-text extraction fallback exists. This uses Anthropic's documented
[custom tool schema and forced selection](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools);
model compatibility must be rechecked if the pinned models change.
The whole-lesson preflight critic also uses one forced strict
`submit_visual_preflight_review` response. Existing local `validateReview` checks
remain authoritative for exact current-field quotes, IDs, source pairs, scope and
clinical disposition. Unsupported read-only coverage contracts must report
`source_gap`; they are not permission to auto-patch `required_concepts` through a
clinical narration repair. Supported scalar source enums constrain output; local
checks still verify the actual source-key/page pair. Wrong/missing/multiple tools,
unexpected text and truncation fail closed without free-text extraction.

Raw-schema compatibility follows the provider's
[documented limits](https://platform.claude.com/docs/en/build-with-claude/structured-outputs):
`anyOf`, scalar enums and `minItems:1` are supported; `oneOf`, object-valued enums
and `maxItems` are not. Three development rebuilds initially returned400 while
this transport was being integrated; their drafts and responses are retained.
After correction, real expert review-only calls for three saved full lessons
returned200/tool_use and ready preflights. This proves observed compatibility,
not source entailment or image quality. The two frozen cohorts remain0/6 before
image generation; these subsequent expert recoveries never replace those results.
The default and expert models each accepted one captured live three-field check
on an existing Forge lesson on 2026-10-17. Two preceding calls were logged as
successful tool responses but lost their full artifacts to a harness path error.
The captured pair made only a punctuation edit and a no-op; they do not prove
useful concision. A fifth call used the earlier v21 Forge draft and shortened
the selected visuals from 23/27/22 to 18/20/18 words, with unselected fields exact.
Independent semantic audit found retained core associations but omitted alcove
clearance and sac floor support; that draft is not evidence of complete spatial
constraint preservation and remains unapproved. Do not promote it to an image run.
These five paid calls are development transport checks, not fresh-topic trials,
clinical approval, image scores, or a measured reliability rate. Independent
delta review and exact preservation checks remain necessary after structured
output: schema conformance cannot establish semantic correctness.

Changed VISUAL fields now receive a separate before/after AI review before the
targeted helper returns a candidate. It sees both complete lessons, the exact
changed pairs, and the original repair instructions, not the writer's rationale.
It inventories identity, count, contact, support, placement, clearance and target
ownership. A changed constraint needs a specific quoted authorization; generic
shortening is not permission. Exact source/proposal quote checks and full original
word-position coverage reject cherry-picked positive inventories. Textual coverage
is attribution only: an AI can still misinterpret a fully quoted relationship.

A valid lost-constraint finding blocks even when the inventory is incomplete;
the preflight ledger marks `evidence_coverage_complete:false` in that case.
Incomplete evidence can never clear a patch. Invalid reviews and lost constraints
do not enter the shorter-format retry loop. The source story remains immutable.
No-op visuals and clinical-only field edits skip this additional request. Each
changed-visual patch adds at most one review request, using the selected default
or expert model; this is a separate AI task, not model-diverse certification.
Superseded operations cannot dispatch that review or deliver its results. Full
source/preflight gates and eventual independent pixel audits still remain required.
Rejected-patch findings are retained in the preflight ledger. Subsequent ordinary
repairs receive only lost-constraint quotes still present in the current original,
explicitly described as advisory retention requirements, not current-story defects.
They never enter clinical contract review or full-redesign old-prop context.

The 2026-10-17 historical regression retained four trial packets under
`Troubleshooting Prompts/preservation_2026-10-17/`: early malformed evidence and
overlength writes failed closed; the final default-model trial rejected both the
known lossy patch and a new lossy patch. One expert-model writer/reviewer pair
produced 22/24/21-word replacements independently checked against the original
constraints with all unselected fields exact. A reviewer initially overflagged a
redundant intensity word; semantic-equivalence guidance was clarified prospectively.
All 11 captured paid responses (180,058 input / 6,524 output tokens, excluding
retrieval and independent agents) are development regression evidence, not a
fresh-topic first-pass rate, default-model success, image approval, or cost saving.
The critic also receives external observations to verify against the new draft;
their presence does not grant approval. Full redesign gives the writer only the
source-reviewed clinical teaching units and unresolved findings, omitting the full
rejected scene, ready-row descriptions and prior patch examples to reduce copying.
Repair mode retains read-only scene context when existing associations should stay.
Optional `repairUnits` (harness `--repair-units 3,4`) limits a coordinated semantic
repair to existing anchor IDs. The writer may update all four fields of selected
units and the shared review script, but must preserve unselected units and scene
architecture. Invalid IDs/duplicates and mixing this with full redesign fail before
repair calls. Changes outside scope are rejected before the gate and after preflight;
approval is invalidated if a downstream patch exceeds the selected scope. The full
medical gate, source review, and visual review still run for all units.

Topic and operation predicates are checked during preflight so superseded lessons
cannot dispatch follow-up repairs. Cancellation releases the Forge button; an old
completion cannot unlock a newer run. Demo delays and rebuild error handling follow
the same topic/operation checks. The browser harness exports completed repair
failures immediately instead of polling until its long provider timeout.

The earlier nine-render CO success is development evidence, not a held-out trial.
See `docs/first-pass-evaluation.md` for evaluation mechanics and dated handoff
entries for actual outcomes. No universal first-render reliability is claimed.
