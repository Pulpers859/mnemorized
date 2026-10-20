# Chapter 1: Broadened Cue Audit

## Scope And Correction

This re-review covers only the same ten selected terms from Tintinalli Chapter 1,
**Emergency Medical Services**. It does not advance to Chapter 2. The earlier
sound-only result remains in `tintinalli-chapter-cue-ledger.json`; zero proposals
under that filter was not evidence that these terms lacked useful visual cues.
The filter wrongly excluded actions, professional characters and conceptual
metaphors from a general association search.

Source provenance and page boundaries are inherited from the saved source audit:
`Tintin_Prehospital Care.pdf`, pages 1-3, SHA256
`856A9EB4746909447C9BD2FD0ABB4D3463669D0234796503828939E9CA67A642`.
Nine terms occur in prose; Emergency Medical Services is a chapter-title match.
Chapter 1 ends above the actual Chapter 2 title block on page 3, not its running
header. No new source extraction or clinical-claim verification is claimed here.
Term occurrence supports vocabulary selection, not the truth of a proposed
mechanism, treatment, or image. These are original/user-suggested design hypotheses.

## Broader Review Method

Generate through phrase/sound play, literal or double meanings, physical
relationships, and familiar character situations. Prefer the simplest useful
representation; do not require every syllable to become an object. An action can
carry the association. An object-naming failure diagnoses ambiguity rather than
automatically vetoing a teachable cue.

Review each proposal against these questions without inventing numerical scores:

1. **Bridge:** Is there an explainable path from the picture to the intended term?
2. **Learned recovery:** After the bridge is taught, could it cue the intended
   concept without the full answer printed in the image? This is a hypothesis
   until tested, not an assertion of successful recall.
3. **Discrimination:** What plausible competing answer must it be tested against?
4. **Static visibility:** Can its meaningful relationship exist in one still image?
5. **Meaning boundary:** Does the metaphor imply an unsupported clinical fact,
   procedure, cause, indication, or outcome? Specify limits or hold it.
6. **Economy:** Does added detail carry meaning, or merely decorate the explanation?

`retain_candidate` means worth preserving for later testing, not production
approval. `hold` means the particular design needs a better distinguishing bridge.
Reject unsafe or misleading variants without rejecting the entire concept.
Source validity, render fidelity and learner recall remain separate judgments.

## Candidate Review

Current structured decisions are mirrored in `chapter-1-cue-audit.json` for the
cross-chapter held-cue register. Update both when revisiting a decision; the
original sound-only ledger remains historical.

| Term / Page | Proposed Cue And Bridge | Decision | Main Limitation / Discrimination Target |
| --- | --- | --- | --- |
| Emergency Medical Services / 1, title | Ambulance crew responding to an emergency; familiar occupational scene | Hold | Useful context, but not a distinctive retrieval hook versus ambulance transport or paramedic. Do not invent a contrived rebus just to fill this slot. |
| paramedic / 1 | Two medics together: **pair of medics**; phrase-based near-sound bridge | Retain candidate | User proposal. Pair-of-medics is not an exact homophone of singular paramedic. Teach the playful compression; test against generic medical team and EMT, without pretending clothing distinguishes licensure. Two figures are enough. |
| defibrillation / 1 | Recognizable defibrillator equipment with a conspicuous electrical discharge; device/action association | Hold | Generic electrocution does not distinguish defibrillation, cardioversion or electrical injury. A magical shock restoring an orderly rhythm adds an unverified clinical claim and a temporal transition. Keep electrical imagery as an ingredient, not a complete discriminative cue yet. |
| hemorrhage control / 1 | A clamp visibly closes a leaking red-fluid pipe; flow-control relationship | Retain candidate | Adapted from user's tied leaking pipe. The leak and closure must remain visually legible. Competes with obstruction or plumbing repair; teach the bleeding metaphor. Not a demonstration of a tourniquet, vessel clamping or use of wire on a patient. No technique or treatment choice is encoded. |
| online medical control / 1 | Physician at a radio console communicating with an ambulance crew; professional direction across a live link | Retain candidate | An illustrative relationship, not a sound bridge. Could be dispatch, telemedicine or a routine call. Requires explicit learned context and later discrimination; no assertion that radio equipment alone encodes medical authority. Avoid tiny screens or printed instructions as the answer. |
| naloxone / 2 | No sufficiently clear name-specific cue proposed in this bounded review | Hold | Do not force a syllable puzzle. A generic lock/key or rescue prop would not uniquely identify this drug. A treatment-related cue would require passage-level evidence and would still need identity discrimination. |
| opioid overdose / 2 | Overflowing medicine cup; excess-quantity metaphor | Hold | Encodes excess medicine, not opioid identity. Can mean another drug, a dose or a spill. Overflow can remain a reusable state ingredient, but is not a complete opioid-overdose association. No diagnostic or dose implication. |
| cardiac arrest / 2 | A heart character visibly wearing handcuffs: heart + **arrest** double meaning | Retain candidate | User proposal. Strong economical identity/relationship hypothesis, not proof of recall. Test against heart attack and generic heart disease. Handcuffs must visibly belong to the heart. Clutching a chest or an X alone is less specific and is not retained as an equivalent. No anatomy, treatment or physiological mechanism is implied. |
| mutual aid / 3 | Two distinct ambulance teams each helping the other; reciprocal helping relationship | Retain candidate | Reciprocal help, not merely two people standing together. A still-image candidate could show each supporting the other's equipment; avoid complex hand choreography. Competes with routine teamwork and partnership. Does not encode administrative agreements or operational rules. |
| surge capacity / 3 | A facility with extra open treatment spaces facing a crowd of arrivals; demand versus available room | Retain candidate | Conceptual spatial metaphor, not a word pun. Crowd alone means demand, not capacity; visible additional room is essential. Competes with overcrowding, evacuation and routine expansion. Do not imply unlimited resources or a numerical capacity. This is not a segmented medical scene specification. |

## What This Establishes

### Independent Challenge And Disagreements

A separate AI reviewer (Russell) reviewed the ten supplied proposals, not the
source PDF or empirical images. It independently retained the same six conditional
candidates and held defibrillation and naloxone. It rejected the overflowing cup
as a complete opioid cue; main agrees the proposed complete cue fails, while
retaining only the generic excess-state ingredient for possible future design.

The reviewer would additionally retain an EMS response scene if given an EMS
badge. Main keeps this on hold: printing the target acronym does not resolve the
weak image-to-term bridge. Its suggested OPIOID label and NALOXONE token are also
not adopted as solutions; printing the answer cannot establish a discriminative
visual association. A defibrillator label may identify a prop but is not evidence
of a successful mnemonic. These disagreements are preserved, not averaged into a
passing score. The reviewer is an AI collaborator, not a credentialed clinician.

Six designs are retained as **untested candidates**; four are held. These are not
six newly proven mnemonics. All ten terms were reconsidered, including the user's
alternatives. The strongest editorial starting points are pair-of-medics and the
handcuffed heart. The more contextual candidates need harder discrimination tests.

The canonical 76-entry catalog remains unchanged: this chapter bank preserves
the broader associations without silently converting them into production
vocabulary or altering historical sound-workshop results. No empirical render,
pronunciation, recognition or delayed-recall evidence was added.

Before admission to a frozen test subset, teach each bridge once and test later
recovery without leading prompts, including its listed distractors. Inspect the
actual generated image separately. A cue may be teachable without being guessed
by a completely untrained viewer, but repeated explanation during testing is not
successful retrieval. No recall threshold or image score is claimed here.

No Forge lesson, clinical narration or image prompt was authored or generated.
No Anthropic API calls, other paid provider calls or image renders were made;
the separate $6 benchmark allowance remains unused by this work.
