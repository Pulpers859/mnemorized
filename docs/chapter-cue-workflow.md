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
   Prefer a frozen term/keyword inventory followed by exact-prior retrieval BEFORE creative decisions, rather than first discovering same-term selected cues during final review. For inventory-only queries, clearly label any `hold` placeholders as lookup adapters, not actual author decisions. Preserve the inventory hash and prior cutoff; rerun only if that inventory changes. An exact lookup cannot replace bounded alias/ingredient checks.
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
- Do not assign a smaller agent merely to launch an existing deterministic script. Main can run it directly. Use a helper only for a bounded task that requires actual interpretation or nontrivial extraction, and count its preparation, review and handoff costs.
- Prefer compact author decisions and explicit exact-prior-copy requests over repeated cue boilerplate, source-coordinate transcription and a bespoke materializer per author. A common assembler must validate both outputs before writing, reject undeclared fields and preserve authored semantic changes. The chapter72-73 trial's source-specific assembler is local evidence, not yet a generic production tool.
- Keep source/keyword inventory and creative decision freezes separate. Record omissions and coordinate corrections before creative authoring too; moving a repair earlier does not erase its cost. Laboratory/testing/imaging operation heads are not automatically excluded merely because they appear in headings. Exclude pure navigation explicitly; extract meaningful heads first.
- Record source and rubric limitations. Account for preparation, stronger review and repair work when discussing efficiency; output bytes and wall time are not billed-token or quota-weight measurements.

## Audited Efficiency Tools

Use `tools/chapter_cue_review_payloads.py` for the optional audited review
representations and narrow editorial preflight. It is stdlib-only, reads local
inputs and emits UTF-8 stdout; it does not write banks, retrieve medicine, call a
provider or grant admission. Save inputs/outputs under the batch's ignored
`Troubleshooting Prompts/` packet. Do not send both representations to a reviewer.

```powershell
python -X utf8 -m tools.chapter_cue_review_payloads lint --input "Troubleshooting Prompts/<packet>/materialized/chapter-N-cue-audit.json"
python -X utf8 -m tools.chapter_cue_review_payloads semantic --input "Troubleshooting Prompts/<packet>/original-review.txt"
python -X utf8 -m tools.chapter_cue_review_payloads evidence --input "Troubleshooting Prompts/<packet>/expanded-retrieval.json"
python -m pytest tests/test_chapter_cue_review_payloads.py
```

- Before reviewer dispatch, inspect editorial warnings after the existing sparse
  build. They flag known undefined-root and unfinished-ingredient-check phrases
  in reasons/comparisons only. Investigate each warning against real evidence;
  quoted historical text can require acknowledgement rather than correction.
  Zero warnings is not semantic, source or schema approval. Do not delete
  qualifications merely to silence a warning.
- The semantic table lists field names once, retaining every value and other
  review lines. Require exact original-text reconstruction. It replaces only
  representation, not all-row coverage or independent stronger review.
- Evidence cards group exact cue/scope/status triples separately within selected
  and held results. Retain every displayed ref, exact term, null scope and record
  multiplicity. Ref abbreviation removes fixed path syntax only; distinct terms
  are not interchangeable. Matched counts remain corpus totals, distinct from
  displayed refs; retain no-hit queries and truncation. Query identity/counts and
  record multisets must round-trip; grouped display order can change.
- Unknown fields or unsupported layouts must not be silently dropped. Use the
  original view when format conversion fails or positional columns impede review.
  This tool does not prove completeness of upstream source/prior evidence.

Local retrospective measurements (2026-10-26): semantic review inputs fell
9.58%/5.43% on chapters91/92; fourteen retrieval-query inputs fell from2,229to
1,728local `o200k_base` tokens (22.48%), including schema/instructions, while
retaining31original and9additional saved displayed records. No new retrieval
occurred. Editorial warnings detected three known historical note defects, not
measured avoided repairs. These are separate surfaces; do not add their
percentages into an app-wide claim. Earlier failed experiments remain failures.

Actual Codex quota, reasoning/cache costs, reviewer comprehension, held-out
quality and setup-adjusted net savings remain unproven. No automatic smaller-model
creative authorship or review-scope reduction is authorized. Use new experiments
only when explicitly requested, with frozen scope/gates, first results preserved,
bounded advisor effort and independent audit. Do not routinely reconvene councils
per chapter. Raw evidence is in the local token_efficiency_council_2026-10-26
packet; tracked tool tests provide standalone integrity regressions.

## Sparse Authoring Contract

`tools/chapter_cue_sparse.py` supports the chapter74-75 trial and later compatible
packets. It is an offline materializer, not a medical gate or semantic reviewer.
Main verifies a packet's source hash and actual chapter-region manifest first.
The author selects meaningful lexical heads and native page/span IDs in
`author/inventoryN.json`; code copies literal text/font/bbox/page into the ignored
inventory evidence. Canonical entries retain compact source pointers and hashes,
not full source excerpts. Source-kind labels, aliases and exclusions still need
human/stronger editorial judgment; valid IDs do not prove complete coverage.

From the repository root:

```powershell
python -m tools.chapter_cue_sparse --packet "Troubleshooting Prompts/<packet>" --chapter N --prepare
python -m tools.chapter_cue_sparse --packet "Troubleshooting Prompts/<packet>" --chapter N --build
python -m pytest tests/test_chapter_cue_sparse.py
```

Prepare BEFORE creative authoring. It freezes the inventory/source-cache hashes,
emits bounded exact-prior leads and freezes the prior corpus. Query `hold` values
are placeholders, not authored holds. Do not regenerate preparation over existing
decisions; preserve the old freeze and explicitly reconcile an approved inventory
repair first. Outputs stay under the ignored packet's `materialized/` directory.

Author decisions declare the exact inventory SHA and cover every term once:

- `reuse`: explicit `[exact term, selected prior reference]` pairs, only after
  reading and approving the actual cue AND scope. Same-casefold name and exact
  inherited cue/scope are required. These intentionally mean unchanged repeat
  and existing-candidate recount; code records that author-selected meaning.
- `changes`: complete semantic decisions for new/modified/aliased cues, scope
  changes, variants, local repeats and holds. Author owns cue/attempt, encoded
  scope, reason and reasoned association comparison. These are not auto-filled.
- Optional `aliases`: explicit canonical-prior adoptions with exactly `term`,
  `prior`, `reason` and `association_comparison`. The stronger author must read
  the actual selected prior cue/scope and explain the target's encoded head and
  omitted modifiers in the reason. Code copies that frozen cue/scope verbatim;
  it records unchanged repeat/existing-candidate recount, never new yield.
  It accepts no cue, scope, status or provenance overrides, no held/restricted
  prior, no missing legacy scope and no local reference. Use a FULL `changes`
  row for actual variants, scope revisions, legacy scope repair, local repeats
  or reconsidered holds. The prior-file hash is bound by `prior-freeze.json`.
  An author-selected alias is not a mechanically inferred clinical synonym;
  independent review must read its per-target notes, not just grouped cue prose.
  Optional alias rows are counted separately in sparse provenance. Older packets
  without this field retain their existing schema behavior. This format is a
  new91-95trial, not a retroactive rewrite or measured token-saving claim.
- `resolved_holds`: explicit local first-draft hold resolutions only; never erase
  another chapter's history just because this chapter selects the term.

If a full semantic decision cites a selected canonical prior while claiming
`unchanged_repeat`, cue and scope must match that prior exactly, irrespective of
the current retain/reuse status. Exception: a genuinely missing/blank legacy scope
may be supplied in a FULL authored semantic row while keeping its cue exact;
code records `legacy_scope_supplied`, and main must review that scope. Sparse
inheritance still rejects missing scopes. Do not manufacture a visual variant
merely to repair missing metadata. A different actual bridge needs its real class;
do not relabel a wording change as creative yield merely to satisfy the tool.
For a same-batch repeat, name the actual local comparison rather than falsely
claiming an unchanged copy of a different older selected root. A held attempt may
be reconsidered explicitly, not inherited as a selected cue.

Main independently reviews the fully materialized cue/scope/source evidence,
preserves first drafts and closes bounded repairs before integrating docs,
ledger/index/holds. Software tests and minimal author files cannot substitute
for that review. Count reusable-tool setup and code-review costs when evaluating
the first trial; author-written bytes are not billed tokens or measured savings.
For later batches, keep the tool unchanged unless a concrete integrity defect
requires a tested repair. Keep a packet-local alias/ingredient supplement only
for observed exact-lookup misses: query, actual prior reference and selection
status, cue/scope excerpt and stronger adjudication. Preserve no-hit results.
Clinical relatedness or a shared prop is not proof of the same lexical bridge;
aliases still require explicit semantic rows, not automatic sparse inheritance.
Report each independent review compactly: bank hash, actual source/keyword/prior
scope checked, counts, exceptions and limits. Each exception names the term,
defect, correction and closure evidence. Keep full evidence locally and recheck
only changed entries and affected metadata after repair. Compress reports, not
review scope. Count advisor preparation and review as effort; a shorter report
or unchanged tool does not establish net billed-token savings.
Main may then call `integrate_reviewed` using a local `main-approval.json` with
the reviewed materialized hashes, explicit source/conceptual review scope/date,
durable report and next-chapter record. It preflights the complete packet and
refuses stale evidence, skipped progress or overwriting an integrated chapter;
it does not grant production admission or run Git/provider operations.

The 81-85 follow-up did not demonstrate lower usage: combined authored bytes per
term rose from461.47to544.19 (first-main-observed proxy), and242full semantic rows
were unchanged repeats. See `chapter-81-85-sparse-workshop.md`. A future explicit
author-selected alias-adoption format may reduce duplicate prose, but requires
separate tool tests, actual selected prior identity/scope and independent review.
Do not change the schema during a frozen batch or auto-admit semantic aliases.

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
