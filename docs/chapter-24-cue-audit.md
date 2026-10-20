# Chapter 24: Cardiac Resuscitation

Original pass: 15 terms, 0 new compositions, 10 reuses, 5 holds.
After main integration on 2026-10-20: **54 terms, 12 retained candidates,
31 reuses, 11 holds**. The 39 additions received main source/conceptual review.
Vasopressin reuses Chapter20; defibrillation reuses Chapter23.
Editorial vocabulary selection, not exhaustive coverage, a protocol, clinical
anchors, narration or image-generation prompts. New composition does not mean
new primitive or original invention. See the dated integration review below.

## Source Checks

Purchased `Tintin_Resuscitation Procedures.pdf`, SHA256
`93ace1119e1628b57d1f22b91fa0b9a3cab0e285086d423b8f033a5b5054e689`.
PDF11-22 = printed153-164, offset +142. Author checked the hash, term positions
and full boundary-page rasterizations. Actual Chapter24 title is right-column
printed153 below Chapter23 references; left-column material is not Chapter24.
Chapter24 ends after full-width Box2/Figure2 and references on printed164,
above the lower-left Chapter25 title. Lower-right continuation there is Chapter25.
Running headers were not used as boundaries. All15 term/page matches checked;
capnography shares a heading, magnesium is unqualified, and oxygen is a body word.
These are vocabulary-location checks, not validation of the source's medical advice.

## Associations

| Term | Printed / PDF | Cue | Decision |
|---|---|---|---|
| Cardiac arrest | 153 / 11 | Handcuffed heart | Reuse |
| Chest compressions | 153 / 11 | Toy treasure chest squeezed by clamp | Reuse Chapter22 |
| Capnography | 153 / 11 | Captain pointing at graph | Reuse |
| Oxygen | 153 / 11 | Oxygen cylinder only | Reuse Chapter22 standalone headword |
| Asystole | 154 / 12 | Flat trace and still heart | Reuse |
| Ventricular fibrillation | 154 / 12 | Fine fiber fringe and heart | Reuse Chapter18 fibrillation family |
| Torsades de pointes | 154 / 12 | Twisted ribbon and pointe shoes | Reuse |
| Sodium bicarbonate | 158 / 16 | Familiar orange baking-soda box and powder | Reuse |
| Magnesium | 159 / 17 | Horseshoe magnet | Reused primitive |
| Hypothermia | 162 / 20 | Shivering mannequin and ice block | Reuse |
| Defibrillation | 153 / 11 | No improved proposal | Existing hold |
| Epinephrine | 153 / 11 | No improved proposal | Existing hold |
| Amiodarone | 153 / 11 | No improved proposal | Existing hold |
| Lidocaine | 153 / 11 | No improved proposal | Existing hold |
| Vasopressin | 153 / 11 | No economical proposal | Newly recorded hold |

## Reuse and Limits

[Structured bank](chapter-24-cue-audit.json) gives per-entry scope, provenance and
limits. Prior chapter banks, catalog and both sound-bridge workshops were searched.
Chapter18 rhythm families and Chapter19 magnesium/drug dispositions were checked.
Main identified same-batch Chapter22 chest and oxygen matches; author checked
both entries and changed provenance to those direct headwords. The standalone
oxygen cylinder inherits Chapter7 ingredients without its pressure chamber;
Chapter21 bank was not present when checked. No competing oxygen primitive added.
Fibrillation fibers do not encode the ventricular qualifier; learned lesson context
must supply it. The treasure chest is wordplay, not a demonstration on a person.
Magnesium does not gain sulfur props. Familiar categories and partial bridges are
allowed without demanding isolated unique identification or every syllable.

Historical holds/rejections remain unresolved. No `resolved_holds` event claimed;
main owns shared register integration. No proprietary scenes imported; generic
overlap cannot be ruled out. No clinical facts, doses, thresholds, mechanisms or
current-guideline endorsement are encoded. Every entry `tested:false`, production
admission false, evidence arrays empty, provider calls and generated images zero.
Source-page rasterizations are source inspection only, not cue-render evidence.
No Git, network, providers, subagents, shared ledger, tests, hold register or handoff
operations. Local source rasters:
`Troubleshooting Prompts/tintinalli_chapter_cues_2026-10-19/chapter24/`.

## Emphasized Keyword Screen: 2026-10-20

Original review date remains 2026-10-19. Original-versus-added membership is
explicit: the 15 rows in Associations above are the original set; the 39 below
are additions, not replacements. Chest compressions/oxygen still reuse Chapter22,
and ventricular fibrillation still reuses Chapter18's family. Vasopressin is
unchanged and main-owned pending the Chapter20 reconciliation.

PyMuPDF span inspection covered all PDF11-22 pages, with actual chapter boundaries
applied on shared pages. Reviewed Bold/Semibold/Black fonts and bold flag16,
including emphasized body phrases, diagram words and meaningful table labels.
Examples: MinionPro-Bold 9pt body; MyriadPro-SemiboldCond 11pt subheadings;
MyriadPro-BlackSemiCn 12/15pt headings; HelveticaLTStd-Bold 8pt figure vocabulary.
Font details per trial are in structured `keyword_screen.items`. Full source-page
rasters at PDF17/19/20 were visually checked as well as the prior boundary rasters.
Annotation enumeration found zero annotations, hence zero highlight annotations.
Flattened/background highlighting is not ruled out by that check.

Whole clinical clauses, numeric instructions, author/header/caption numbering,
references and generic table column scaffolding are excluded, not held. Their
meaningful lexical words were separated before trying cues. QTc prolongation
preserves the source's small regular-font c between bold QT and prolongation;
the reused long-QT objects do not encode that qualifier. Source Chapter26's
bold return-of-spontaneous-circulation text on PDF27 is outside both this screen
and Chapter25; Chapter24 ROSC is independently bold on PDF15.

Separate unformatted table additions: **none**. Oxygen is an existing entry
screened again at regular-font Table24-1; airway/breathing/circulation additions
also have actual bold diagram labels on PDF13. Meaningful regular table labels
were reviewed without mislabeling their typography.

| Added term | Printed / PDF | Decision |
|---|---|---|
| extracorporeal membrane oxygenation | 154 / 12 | hold |
| Chain of Survival | 154 / 12 | retain_candidate |
| Primary Survey | 155 / 13 | retain_candidate |
| Secondary Survey | 155 / 13 | retain_candidate |
| vascular access | 157 / 15 | retain_candidate |
| pulseless electrical activity | 156 / 14 | hold |
| ventricular tachycardia | 159 / 17 | reuse_candidate |
| bradycardia | 158 / 16 | reuse_candidate |
| beta-blockers | 159 / 17 | reuse_candidate |
| atropine | 159 / 17 | hold |
| calcium | 159 / 17 | reuse_candidate |
| hypomagnesemia | 159 / 17 | reuse_candidate |
| hypocalcemia | 159 / 17 | reuse_candidate |
| QTc prolongation | 159 / 17 | reuse_candidate |
| hypovolemia | 161 / 19 | reuse_candidate |
| hemorrhage | 161 / 19 | reuse_candidate |
| hypoxia | 161 / 19 | retain_candidate |
| acidosis | 161 / 19 | reuse_candidate |
| hyperkalemia | 162 / 20 | reuse_candidate |
| hypokalemia | 162 / 20 | reuse_candidate |
| cardiac tamponade | 162 / 20 | reuse_candidate |
| tension pneumothorax | 162 / 20 | hold |
| coronary thrombosis | 162 / 20 | retain_candidate |
| pulmonary embolism | 162 / 20 | reuse_candidate |
| targeted temperature management | 163 / 21 | retain_candidate |
| glycemic control | 163 / 21 | retain_candidate |
| neurologic assessment | 163 / 21 | retain_candidate |
| selective aortic arch perfusion | 164 / 22 | hold |
| airway | 155 / 13 | reuse_candidate |
| breathing | 155 / 13 | reuse_candidate |
| circulation | 155 / 13 | retain_candidate |
| drug overdose | 162 / 20 | retain_candidate |
| cardiac glycoside toxicity | 159 / 17 | hold |
| cocaine toxicity | 159 / 17 | hold |
| sodium channel blockade | 159 / 17 | reuse_candidate |
| advanced cardiac life support | 155 / 13 | retain_candidate |
| ROSC | 157 / 15 | retain_candidate |
| Cardiac Arrest Sonographic Assessment | 159 / 17 | hold |
| trauma | 161 / 19 | retain_candidate |

The structured screen also links existing emphasized entries and records
non-term exclusions. ROSC was reconsidered after the user's rose proposal:
a single rose qualifies as a partial learned name cue, not exact homophony
(rose ends in z for many speakers, spoken rosk in sk). Learners spelling the
acronym aloud need separate teaching. ROS/other rose-name collisions remain;
no acronym expansion, clinical outcome or circulation mechanism is encoded.
The initial returning-arrow/heart attempt is still recorded in the JSON reason.
This changes a draft screen decision, not an older shared hold.

Prior banks/catalog/workshops remain the reuse check;
new proposals use generic vocabulary objects, not source illustrations or
clinical mechanisms. Neither every word in every table nor all medically key
concepts is claimed covered by PDF typography extraction. No new entry has
independent approval, render/recall evidence or production admission. All entries
remain untested; evidence empty and spend zero. Only assigned files/source rasters
changed; no global integration, tests, Git, provider or network operations.

## Main Integration: 2026-10-20

Final: **54 terms / 12 new candidate compositions / 31 reuses / 11 holds**; 54 linked keyword-screen items. This dated section supersedes draft counts and pending-review language above. Main independently checked source locations/boundaries and conceptual scope; no empirical validation. Typography is not an exhaustive key-concept census. Zero highlight annotations were found; printed emphasis was screened separately.

Defibrillation, vasopressin, Chain of Survival and circulation reuse Chapters23/20/22 candidates after cross-bank reconciliation, not new discoveries.
