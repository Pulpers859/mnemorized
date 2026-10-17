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
