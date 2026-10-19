# Visual Cue Catalog

## Purpose

`docs/visual-cue-catalog.json` is the structured source of truth for **offline design candidates**, not a source of medical facts. It currently contains 72 entries: 54 candidates, 17 unverified legacy mappings, and one restricted mapping. No entry has measured recall evidence. No new entry is automatically injected into Forge.

Keep three questions separate: Is the lesson medically sourced? Does the image depict the specified cue? Can a learner recover the intended concept later? A successful render answers only the second question. This catalog cannot replace Forge retrieval, the medical gate, an independent pixel audit, or learner testing.

## Design Grammar

Prefer a reusable identity + state + relationship, rather than inventing a different elaborate pun for every topic. These are vocabulary examples, not medical scene scripts:

| Concept | Candidate representation | Important limitation |
| --- | --- | --- |
| Potassium excess | Bananas exceeding a container's rim | User-proposed reference example; not dietary causation or a clinical cutoff |
| Potassium deficit | Sparse bananas in an explicitly learned capacity reference | Sparse quantity alone could mean a serving or dose |
| Glucose excess / deficit | Sugar contents above / well below the learned reference | Sugar can resemble salt; reject if ingredient identity is unclear |
| Magnesium excess / deficit | Magnet contents above / below the learned reference | Magnet-to-magnesium is an unvalidated learned bridge |
| Sodium excess / deficit | Salt contents above / below the learned reference | Salt is not automatically saline or a treatment |
| Calcium excess / deficit | Bone-shaped token contents above / below the learned reference | Strong collision with actual skeletal anatomy |
| Obstruction / narrowing / rupture | Plugged opening / continuous narrowed tube / broken boundary | These states are distinct; do not substitute one for another |
| Branching / convergence | Shared stem with separated limbs | A symmetric Y alone cannot establish direction |
| Inside / outside | Token and an intact transparent boundary | Position does not establish active exclusion or transport |
| Ataxia | Taxi sound bridge | Missing weak vowels; learner must already know the spoken bridge |
| Carpal | Car + pail near-sound bridge | Vowel reduction required; cannot distinguish carpel |
| Rales | Railway rails sound bridge | Only for a learner using the RAYLZ pronunciation |
| Suture | Suit + chair near-sound bridge | Imperfect compressed pronunciation; not a procedural depiction |

For electrolyte/glucose examples, container quantity is a learned metaphor, **not a measurement of serum concentration**. Never derive diagnosis, severity, treatment or normal ranges from an illustration. Clinical claims must already be independently grounded by Forge.

## Entry Contract

Every entry records identity/aliases, cue type, one or two principal objects, the intended bridge, applicability, exclusions, a visible signature, collision tags, status, provenance, and separate render/recall evidence lists. Repeated tokens are a material group, not a requirement for an exact visible count. A source reference establishes provenance, not effectiveness.

- `candidate`: proposed, not tested or production approved.
- `legacy_unverified`: inherited vocabulary, not established effectiveness.
- `restricted`: known contextual concern; excluded from ordinary searches.

An empty evidence list means no qualifying evidence recorded. Do not manufacture audits, promote status based on citations, or treat absence of a reported failure as a pass. `docs/visual-cue-evidence.md` preserves one narrow reported failure without claiming general proof.

## Offline Tools

From the repository root:

```powershell
python tools/visual_cue_catalog.py --validate
python tools/visual_cue_catalog.py --query hyperkalemia --limit 3
python tools/visual_cue_catalog.py --query obstruction
python tools/visual_cue_catalog.py --query clock --include-restricted
python -m pytest tests/test_visual_cue_catalog.py
```

Search uses literal token overlap, not clinical reasoning or semantic retrieval. It returns at most eight entries, always with an unvalidated-design caveat. It never fills missing concepts or calls an AI provider. A matching result is not an endorsement or a clinical recommendation.

## Review And Admission

The follow-on [sound-bridge workshop](sound-bridge-workshop.md) covered 103 distinct terms/headwords in 104 attempts and added only 11 untested candidates after independent review. Sixteen are held outside this catalog; 76 distinct terms were rejected. This is not 50 new usable sound bridges. The full structured workshop/rejection bank is `docs/sound-bridge-workshop.json`.

The October 19, 2026 review used AI language/wordplay, visual-composition and software-validation reviewers, not human medical specialists. The wordplay lane proposed 24 items, rejected 17 itself, and provisionally retained seven. Main curation admitted only four of those seven as untested candidates: carpal, ataxia, rales and suture. Antrum, tarsal and rigor were withheld because object naming or sound reduction was too fragile. A separate 36-item composition proposal set was screened; many arbitrary ingredient/state combinations were not added. More proposals do not equal more useful cues.

The raw proposals and rejection rationales are retained locally in `Troubleshooting Prompts/cue_catalog_2026-10-19/`; that ignored experiment folder is not required to validate the tracked catalog. Pronunciation judgments are provisional, not a pronunciation dictionary. Independently proposed mappings can overlap common existing mnemonics; originality has not been legally or exhaustively verified.

Before production admission, require unprompted object identification, term/state discrimination against plausible distractors, source-scoped applicability, collision checks across lessons, independent first-render auditing, and delayed learner recall. Record failures as well as successes. Freeze any selected subset before a paid benchmark; do not change mappings midway or claim first-pass reliability from repaired examples.

## Research Boundaries

Public descriptions from [Sketchy](https://www.sketchy.com/blog/how-to-remember-tough-mcat-topics), [Picmonic](https://www.picmonic.com/about) and [Pixorize's public blog](https://blog.pixorize.com/2021/06/14/how-to-study-complex-material-online-helpful-tips-for-medical-students/) informed general principles: distinct visual cues, stable associations, narrative/spatial context, and retrieval practice. No proprietary scene, signature character system, course asset or competitor cue catalog was imported. Pixorize's main site returned HTTP 403; no access control was bypassed.

A [2014 randomized study of another audiovisual mnemonic system](https://pubmed.ncbi.nlm.nih.gov/24868180/) assessed recall and question performance. It does not validate these entries, this app, or image-generation reliability. Marketing claims are not entry evidence.

This expansion used no Anthropic API calls or image renders. The separately authorized $6 Anthropic benchmark ceiling remains a ceiling, not evidence of a completed benchmark.
