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
   injects the canonical Constitution and bounded private source excerpts. The
   critic checks all clinical text, the narration-to-visual associations, every
   required visual relationship, and the whole scene's physical conflicts.
4. Deterministic validation requires every stable anchor ID exactly once,
   verbatim relationship spans, retrieved source references, explicit dispositions,
   and consistent risk/clearance fields. These checks validate the review contract;
   they do not make the critic's semantic judgment infallible.
5. One targeted source-grounded clinical correction may run before visual text is
   locked, limited to specifically cited anchor/narration/review-script fields.
   It must pass the medical gate and critic again. Source gaps still block.
   Then at most two visual-only repair requests run, including rejected patches,
   followed by fresh whole-lesson review. HOOK, clinical text, review script and
   required scope remain identical throughout visual repair. A new association
   requires explicit Forge redesign, not an unreviewed visual patch.
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

The earlier nine-render CO success is development evidence, not a held-out trial.
See `docs/first-pass-evaluation.md` for evaluation mechanics and dated handoff
entries for actual outcomes. No universal first-render reliability is claimed.
