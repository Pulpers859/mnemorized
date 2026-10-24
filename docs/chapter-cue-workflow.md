# Chapter Cue Workshop Workflow

Use this workflow for the offline Tintinalli vocabulary library, normally five chapters per batch. It does not replace Forge source retrieval/medical gating, authorize image generation or admit cues to production. Standing cue criteria remain in [Review And Admission](visual-cue-catalog.md#review-and-admission).

## Tested Division Of Work

Patrick approved this allocation after the [paired agent pilot](agent-workflow-pilot-2026-10-23.md):

| Lane | Appropriate Work | Must Not Own |
| --- | --- | --- |
| Smaller/lower-usage helper | Bounded literal-head extraction, exact prior-record retrieval, deduplication, schema/reference/count checks, concise bookkeeping | Final cue creation/selection, accept/hold/reject decisions, interpretation of clinical source meaning, provenance adjudication or admission |
| Stronger author/curator | Wordplay, useful partial/category/action cues, scope/collision judgment, actual-host/variant selection and explicit hold resolutions | Self-certifying independent approval |
| Non-author stronger reviewer | Source/lexical coverage, cue/scope/actual-prior review, disputed holds and repair-delta rechecks | Grading its own authored cues or claiming empirical recall/render evidence |
| Main integrator | Source boundaries/risk decisions, final integration/validation, holds register, commits/pushes, billing/secrets | Delegating away final accountability |

Smaller-agent output is assistance, not authority. Confirm the available model/effort for the assigned lane; follow tool/user model-selection permissions. Do not silently downgrade an existing high-judgment lane, upgrade providers, spawn a replacement cohort or create another paid allowance. Resuming a bounded existing expert context may be cheaper than reconstructing it.

The pilot did NOT establish equivalent end-to-end cue authorship or net token/dollar savings. Extraction on prepared excerpts was close; independent whole-PDF boundary discovery, arbitrary OCR/typography and full-chapter reliability were not tested. Do not generalize its numbers into a medical/image/recall score.

## Batch Procedure

1. Recover the last integrated chapter and unfinished author/audit freezes from `docs/handoff.md`. Resume those files/agents; don't restart source/corpus passes or skip a partial chapter. Save raw evidence under `Troubleshooting Prompts/`.
2. Main or a qualified source reviewer verifies the purchased PDF hash, actual title/mixed-column boundaries, printed offset, native fonts/highlight annotations and necessary rasters. Reuse saved evidence when unchanged. Whole-page running headers and an image-block-only scan are not ownership/coverage proof.
3. Give a smaller helper a bounded region or specific mechanical question. Extract meaningful bolded/highlighted/heading/table/figure heads, including named heads inside larger statements before excluding numeric/procedure prose. Return literal wording/region, explicit aliases, omissions/uncertainty and actual prior-record snippets. Do not dump every incidental body word or the entire library.
4. Use deterministic parsing/search/checks for exact refs, duplicate keys, counts and hold preservation. Search term roots AND actual cue ingredients. A returned old hold is not a selected root; a selected generic host is not proof its specific new subtype already existed. Helper flags are leads requiring stronger adjudication, not automatic semantic decisions.
   Before freezing, run `python tools/chapter_cue_prior_matches.py --bank docs/chapter-N-cue-audit.json --limit 3` and save the report locally. Resolve flagged same-term selected priors explicitly. This exact casefold lookup is read-only and cannot find all aliases, shared heads or visual ingredients; it does not automatically accept a cue or overturn an intentional hold.
5. Stronger author makes every cue/hold decision under the unchanged broad rubric. Familiar categories/packaging, actions/relationships and partial names may omit modifiers; unique untrained naming or all syllables are not universal requirements. Reject wrong lexical subtypes, undefined visual objects, arbitrary topic props or unsupported specificity. Record actual encoded scope, collision/naming uncertainty, exact prior roots, declared variants and earlier attempts. All candidates remain untested/nonproduction.
   Absence of an older selected bridge is not a reason to hold a useful new proposal. An unrelated generic-bottle placeholder records nonselection, not a meaningful creative trial or proof of exhausted possibilities. Keyword mappings must name the actual head tried: clinically related words are not lexical aliases, and full statements require explicit extracted-head notes.
6. Freeze author JSON/MD hashes. A non-author stronger reviewer checks the real source regions, meaningful lexical screen and actual prior ingredients once. Report counts/hash and exceptions, not a repeated annotated copy of every entry. If finding-free, state the review scope and limits. Main independently corroborates material findings.
7. Repair only concrete findings, preserving original attempts/holds and first snapshots. Recheck changed entries/mappings and affected counts/refs; do not repeat a full chapter/source audit after a bounded delta. Any newly introduced defect remains open. Do not repair indefinitely to force a score or run a new paid cohort without scope/budget.
8. Main integrates only genuinely closed banks, ledger/index and handoff. Preserve every older hold in the separate revisit register; a term retained elsewhere does not resolve it. Run `python tools/chapter_cue_holds.py --write`, then `--check`, focused chapter/keyword/hold tests and realistic repo validation before commit/push. Report separately source/editorial review, software checks and untested clinical/recognition/recall/render claims.

## Compact Contracts And Repairs

- Specify owner, exact input/output files, allowed writes, required schema, source scope, tool/read budget, acceptance limits and reporting format in each assignment.
- Keep the useful summary small: counts, freeze hash, changed files, validation, exceptions and uncertainty. Store long source/lookup evidence locally; avoid repeated multi-megabyte prior dumps and per-record audit narration.
- Require a FULL schema-conforming replacement when that is needed. If explicitly requesting an overlay, define base hash, exact term-key replacements and extraction add/remove operations. Validate/materialize it deterministically; retain raw first/repair artifacts. Never silently infer missing content or call a patch/full-format ambiguity a clinical failure.
- Scripts establish structure/reference identity, not semantic cue quality. A model's own schema check is not an independent audit. No promotion or generation success based only on passing tests.
- Record source and rubric limitations. Account for preparation, stronger review and repair work when discussing efficiency; output bytes and wall time are not billed-token or quota-weight measurements.

## Count Associations, Not Just Props

The unit of creative yield is the **term-to-image association**, not a previously
unused visual ingredient. Historical `new_candidates` / `reused_candidates`
fields often count ingredient families; do not present them as counts of new
useful associations. They remain historical bookkeeping, not proof of creativity
or of exhausted chapter opportunities.

For new association reviews, report these separate editorial classes:

- `new_association`: a different lexical/conceptual bridge, even if its prop was
  used for a different medical term. Record the actual prior term and image.
- `meaningful_variant`: the same bridge with a substantive change to shape,
  action, relationship or encoded scope. Explain the added value.
- `unchanged_repeat`: the same bridge and substantially the same depiction;
  spelling, inflection or incidental scene changes do not create a new item.
- `hold`: no selected usable association in this review; preserve the attempt
  and reason without claiming a better association is impossible.

Ingredient provenance remains a separate axis. Bread-bun versus bread, calculator
versus adding machine, or toothbrush versus paintbrush requires judgment about
the association, not automatic rejection or acceptance by shared object family.
Changing the medical term alone is not sufficient if the bridge is unchanged.
Count synonyms and repeated appearances transparently; do not sum chapter
occurrences into a claim of unique library growth without cross-bank review.

State the comparison universe. A bounded second look can identify useful new
proposals relative to named records but cannot establish corpus-wide novelty.
Never infer these classes mechanically from the old decision or a term mismatch.
Keep historical root counts and first decisions intact. A supplemental candidate
does not silently resolve the original hold or enter production; changing a
canonical hold still requires explicit bank history and register regeneration.
Independent editorial review does not establish learner recall or render quality.

Keep selection and review provenance separate from novelty. Supplemental records
must declare `selection_status` (`candidate` or `hold`) and `change_origin`
(`existing_candidate_recount`, `reconsidered_attempt` or `new_revision`). A useful
unchanged attempt may be selected without being newly invented; a held attempt
can be a repeat without being accepted. Report fresh revisions separately from
existing bridges rediscovered by better accounting. Do not turn a relabeling
exercise into a claim of newly expanded library size.

Starting with chapter 67, initial chapter banks also record these three axes on
each entry, plus a reasoned `association_comparison`. Initial discovery may use
`change_origin: new_proposal`; that means proposed in this chapter review, not
proven original or empirically effective. Preserve the old decision/count fields
for reference tooling, but label those as ingredient/reference bookkeeping rather
than creative yield. Report association occurrences separately; chapter repetition,
aliases and shared head bridges prevent an automatic unique-library-growth total.

An `unchanged_repeat` is not a freshly authored depiction: its origin is
`existing_candidate_recount` or, for a reselected local held attempt,
`reconsidered_attempt`. A newly authored `meaningful_variant` uses `new_revision`.
Do not let default origin values turn unchanged repeat records into fresh yield.

## Resume Record

After each batch or interruption, record last completed chapter, unfinished chapter numbers, exact author/audit hashes, open findings, held-cue preservation state, agent IDs/roles, validation run and next action. Keep this separate from claims of completion. Mirrored repo delegation skills and `AGENTS.md` link here so future agents recover the same division of work.
