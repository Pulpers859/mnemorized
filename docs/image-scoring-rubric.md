# Mnemorized Image Scoring Rubric (CANONICAL)

**This is the single source of truth for grading generated memory-palace images.**
Every grader — the in-app Image Quality Gate (`frontend/scripts/forge-image-audit.js`),
the offline QA packs (`tools/visual_qa_pack.py`, `tools/stress_visual_pipeline.py`),
any manual audit, and any subagent asked to score an image — MUST use this rubric and
this arithmetic. Do not invent a private scale. If two graders follow this document
they must produce the same number.

Related: `docs/gemini-constitution.txt` (VISUAL ENCODING HIERARCHY + failure modes),
`docs/visual-metaphor-library.txt` (sanctioned metaphors), and
`docs/visual-mnemonic-prompt-contract.md` (prompt/repair rules). Where any of those
describe *how to grade*, this file wins.

---

## 1. Method — deterministic, reproducible

Grade in this exact order and **always show the arithmetic**:

1. Start each of the six categories below at its full point value.
2. Apply the per-defect deductions listed under each category (a category may not go
   below 0).
3. `RAW = sum of the six category scores` (max 100).
4. Determine every **hard gate** that is triggered (Section 3). Each gate has a cap.
5. `OVERALL = min(RAW, lowest triggered gate cap)`, rounded to the nearest integer.
6. Map to a DECISION using Section 4.

A grader that cannot show how it reached the number has not followed the rubric.
When genuinely torn between two category scores, **choose the lower** (Section 5).

---

## 2. Categories (weights sum to 100)

Anchors and hooks together are worth 50 — they are the product. Everything else
supports them.

### A. Anchor Completeness — 30 pts
Full marks: every anchor in the list is present AND identifiable by its visual, not by
a label alone.
- −10 per anchor that is **absent** or **unidentifiable** at normal viewing size.
- −5 per anchor that is present but so tiny/crowded it reads as background clutter.
- −3 per anchor identifiable ONLY because of an attached text label (no shape/hook).
(See also hard gate G1 — missing anchors also cap the OVERALL score.)

### B. Hook Fidelity — 20 pts
Full marks: each anchor uses the strongest available encoding from the constitution's
VISUAL ENCODING HIERARCHY — a sanctioned pure-visual metaphor where one exists
(banana = potassium, salt shaker = sodium, box of baking soda = bicarbonate, skull =
toxicity, hourglass = time, turtle = slow, padlock = restricted, etc.).
- −8 per anchor rendered as **text slapped on a generic prop** (barrel/wall/crate/plaque)
  when a sanctioned metaphor or stronger hook existed. This is the primary failure this
  rubric exists to punish. (See hard gate G6.)
- −4 per anchor whose visual is a weak/arbitrary object that carries no association.
- −2 per anchor that uses a lower hierarchy tier than warranted (e.g. a bare label where
  a hybrid metaphor+label was easy).
Threshold DECISIONS legitimately use functional/contrast hooks (e.g. traffic-light for
K⁺ bands) — do NOT deduct for a correct non-metaphor tier on a decision anchor.

### C. Silhouette & Legibility — 15 pts
Full marks: every element reads by shape first, large, uncluttered, in a wide format.
- −5 illegible clutter / anchors shrunk into indistinct shelf detail.
- −4 duplicated identical silhouettes that blur which anchor is which.
- −3 scene so busy the reading path is lost.

### D. Text Discipline — 15 pts
Full marks: labels are sparse, short (≤3 words on ordinary props), correctly spelled,
and only used where the hierarchy allows (thresholds/doses/acronyms).
- −6 per **misspelled or invented required label** (also hard gate G2).
- −5 meta-instruction / caption leakage — words like "Hook", "Encodes", "zone", zone
  names, speech bubbles, or directional words rendered as visible text (also G3).
- −3 per object overloaded with a crammed multi-line label list.
- −2 per unnecessary label on an object whose metaphor already carried the meaning.

### E. Medical Fidelity — 10 pts
Full marks: nothing in the image implies a wrong fact, threshold, dose, or relationship.
- −10 an implied fact is medically **wrong** (also hard gate G5 — caps OVERALL).
- −4 a threshold/dose is ambiguous or easily misread.

### F. Scene Coherence & Composition — 10 pts
Full marks: one coherent spatial scene with a clear zone sequence in 16:9.
- −6 scene rendered as a **segmented grid / booths / bays / storyboard panels** instead
  of one room (also hard gate G4).
- −3 incoherent spatial placement (anchors floating with no environment logic).
Note: a sanctioned metaphor that is deliberately off-theme is NOT a coherence defect —
the bizarreness effect is intended and wins over theme consistency. Do not deduct here
for an incongruous but correct metaphor.

---

## 3. Hard gates (caps that OVERRIDE the sum)

A gate does not subtract points; it puts a ceiling on OVERALL. `OVERALL = min(RAW, every
triggered cap)`. These make the rubric strict: a beautiful plate that is missing an
anchor still cannot pass.

| Gate | Trigger | Cap on OVERALL |
|------|---------|----------------|
| G1 | Exactly 1 required anchor missing/unidentifiable | 79 |
| G1 | 2 required anchors missing/unidentifiable | 70 |
| G1 | 3+ required anchors missing/unidentifiable | 55 |
| G2 | Any misspelled or invented **required** label | 88 |
| G3 | Meta-instruction / caption / zone-name text leaked into the image | 85 |
| G4 | Scene is a segmented grid / booths / panels, not one coherent scene | 80 |
| G5 | Any medically wrong fact or threshold implied | 75 |
| G6 | Any anchor encoded ONLY as text on a generic prop (no visual hook) when a sanctioned metaphor/stronger hook existed | 90 |

Multiple gates → use the lowest cap.

---

## 4. Decision mapping (deterministic)

Compute OVERALL, then:

- **PASS** — OVERALL ≥ 96 AND none of G1, G2, G5 triggered. Publishable A+.
- **PASS_WITH_TEXT_RISK** — OVERALL ≥ 90, no G1/G5, but a text-discipline gate (G2/G3)
  or an over-text hook (G6) is present. Strong image, needs a text-only tightening pass.
- **REPAIR** — 70 ≤ OVERALL ≤ 95 with a bounded, fixable defect. Use a repair prompt
  (see contract Repair Loop Rules; max 5 iterations).
- **REGENERATE** — OVERALL < 70, or 2+ anchors missing (G1), or the hook strategy itself
  is wrong. Redesign the encoding, do not patch wording.

Never call an image PASS if any anchor is missing, regardless of how the rest scores.

---

## 5. Anti-inflation rules (mandatory for every grader)

1. **External auditor only.** The model that generated the image must never grade it —
   self-grading inflates 15–20 points.
2. **A label alone never satisfies an anchor.** The anchor needs a recognizable shape,
   character, object interaction, or spatial placement. Text on a prop is not a hook.
3. **Treat labels as unreliable** unless they are clearly legible and correctly spelled.
4. **Do not invent anchors** that are not actually visible in the image.
5. **Numeric thresholds/formulas are allowed only when attached to a visible device**,
   not floating.
6. **Tie-break downward.** Uncertain between two scores → take the lower.
7. **Density realism.** Plates with >8 encoded anchors crowd and lose fidelity; when an
   auditor reports "all anchors present and perfect" on a 10-anchor plate, re-verify —
   the in-app vision auditor under-detects on dense plates (2026-07-07 finding).

---

## 6. Required output format

Every grader emits exactly this plain-text block (no markdown), so results are parseable
and comparable across agents:

```
OVERALL_SCORE: <integer 0-100>
DECISION: <PASS | PASS_WITH_TEXT_RISK | REPAIR | REGENERATE>
CATEGORY_SCORES: A:<0-30> B:<0-20> C:<0-15> D:<0-15> E:<0-10> F:<0-10>
RAW_SUM: <integer 0-100>
GATES_TRIGGERED: <e.g. "G1(1 missing) cap79; G6 cap90" or "none">
ANCHORS_PRESENT: <integer>/<total>
MISSING_ANCHORS: <comma-separated anchor numbers, or none>
TOP_ISSUES: <up to 3 short phrases separated by "; ", or none>
REPAIR: <one or two sentences on the single highest-impact fix, or none>
```

`OVERALL_SCORE` must equal `min(RAW_SUM, lowest gate cap)`. If they disagree, the grade
is invalid and must be recomputed.

---

## 7. Score bands (interpretation)

| Band | Meaning |
|------|---------|
| 96–100 | A+ — publishable board-study plate. Every anchor shape-first; text sparse/correct; coherent. |
| 90–95 | A — publishable after a trivial nit; usually a text-discipline tighten. |
| 80–89 | B — one real defect; targeted repair, not regeneration. |
| 70–79 | C — a weak or missing anchor, or a systemic text problem; repair or redesign that hook. |
| < 70 | Regenerate — redesign the encoding strategy. |

Changelog: created 2026-07-07 to unify four divergent scoring conventions (in-app
vibes score, offline structural −30/−12/−5, a 9×0–10 manual card summing to 90, and a
"score harshly" free-form prompt) into one deterministic, gated standard.
