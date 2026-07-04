# Visual Mnemonic Prompt Contract

This is the durable prompt contract for Mnemorized medical image generation. It exists so future agents can improve the system without rediscovering the same failure modes.

## Goal

Generate original, publishable medical memory-palace scenes where learners can recall facts from shape, identity, object relationships, and spatial position before they rely on labels.

The scene should feel like a dense hand-drawn educational visual mnemonic map, not an infographic, checklist, or pile of labeled props.

## Prompt Structure

The Forge pipeline uses this sequence:

1. Clinical concept extraction: identify the 8-12 essential, exam-relevant facts.
2. Story and anchor generation: produce 8-10 anchors, each with `HOOK`, `NARRATION`, `VISUAL`, and `ANCHOR`.
3. Image prompt generation: create an empty room first, then place all anchors into stable spatial zones.
4. Visual QA loop: our prompt -> Gemini image -> Gemini/image audit against our anchor table -> prompt repair -> regenerate.

Do not skip the visual QA loop for high-value catalog or medical-safety content.

## Non-Negotiable Rules

- Every anchor needs a clear `HOOK`: sound-alike, look-alike, functional, contrast, or spatial.
- Every anchor must pass the silhouette test: the cue should still mean something with text removed.
- The image must preserve left, center, right, foreground, and background zones.
- All anchors must be present in one coherent static scene.
- No anchor may become tiny shelf clutter. At 1024px width, the major cue should still be identifiable.
- Text is allowed only when it adds precision or a mnemonic name. Text must not be the whole mnemonic.
- Exact labels matter. If a prompt says `LENA INN`, `ASPIRIN`, or `Gap = 8-12`, do not invent a near-spelling.
- Compact formulas and thresholds are allowed when they are the tested fact.
- Formula labels must sit on a visual device: scale, ruler, gauge, dial, cabinet, chalk mark, plaque, or similar.
- Do not render `Hook`, `Encodes`, zone names, or meta-instructions into the image.

## Precision Text Exception

Some medical topics cannot be taught honestly without numbers or formulas. Examples:

- normal anion gap `8-12`
- anion gap formula
- delta-delta ratio
- Winter's formula
- osmolar gap calculation and `>10`
- drug doses, scoring cutoffs, time windows, and diagnostic thresholds

Use numbers/formulas as precision plaques attached to strong visual mnemonics. The formula should confirm the cue; it should not replace the cue.

## Design Principle Sources

It is acceptable to study visual mnemonic products and local educational videos for reusable design principles:

- sound-alike characters
- silhouette-first object design
- one-room spatial maps
- exaggerated scale and contrast
- object interactions that encode mechanisms
- sparse labels used for precision
- rapid visual review paths

It is not acceptable to copy or closely paraphrase proprietary scenes, character names, recurring symbols, layouts, or fact-to-symbol mappings. The app should learn the grammar of effective visual mnemonics, not clone someone else's vocabulary.

## Gemini Image Generation Guardrails

> **Canonical source**: `docs/gemini-constitution.txt`
>
> The FastAPI prompt director endpoint (`POST /api/gemini/prompt-director`)
> and the local tools (`tools/stress_visual_pipeline.py`,
> `tools/visual_qa_pack.py`) load the constitution file at runtime. Edit
> `gemini-constitution.txt` to change generation rules — do not maintain
> competing inline copies.

These rules are derived from stress-testing Gemini's image generation across multiple topics and iteration cycles. They apply to all prompt generation and repair workflows.

### What Gemini CAN render reliably
- Distinct objects with clear silhouettes (characters, animals, props, furniture)
- Specific materials and states (glass, metal, liquid, fire, broken, deflated)
- Text labels of 1-4 words attached to objects (plaques, stamps, signs, gauge faces)
- Coarse spatial placement: LEFT, CENTER, RIGHT, FOREGROUND, BACKGROUND
- Size contrast between objects (small vs. massive, close vs. distant)
- Artistic styles (ink-and-watercolor, hand-drawn, cartoon)
- Color and lighting (warm amber, spotlight, shadow)

### What Gemini CANNOT render reliably
- **Micro-poses**: interlocked fingers, balloon-puffed cheeks, specific hand positions, exact joint angles, precise facial expressions. These are silently ignored and cause the overall scene to drift.
- **Ground/surface contrast at specific locations**: "pristine sawdust here, scorched ground there" — Gemini applies surface effects based on the nearest obvious cause (fire → scorch under fire source), not where you place them in the prompt.
- **Compound spatial positions**: "center-left" → renders as center. "foreground-right corner" → ambiguous. Use single-axis terms only.
- **Shape-morphing**: flames shaped exactly like a specific letter, clouds forming a word. Sometimes works for large bold numerals; fails for complex shapes.
- **Abstract concepts rendered visually**: "dysregulated host response" cannot be drawn. Must be encoded as a concrete object or character.
- **More than ~3 spatial constraints per figure**: "standing in the left ring, leaning forward, right knee bent, hands at navel" — Gemini honors 1-2 of these and ignores the rest.
- **Clock hand positions**: "hands frozen at one o'clock" is silently ignored. Gemini renders random clock hand positions. Use text labels ("1 HR" plaque) instead.
- **Ambiguous motion verbs**: "crossing the line" may render as approaching. Use completed-state language: "ALREADY PAST the line," "boot planted BEYOND the line."
- **Action-state ambiguity**: "ready to exhale," "preparing to throw," or any "about to X" phrasing renders as actively doing X. Gemini defaults to active states. To show a character waiting/idle, describe completed inactivity: "arms FOLDED ACROSS HER CHEST," "torch resting on the ground," "standing still, WAITING."
- **ALL-CAPS leakage**: Any word in ALL-CAPS in the prompt may be rendered as visible text in the image, even if it is a scene direction, not a label. Reserve ALL-CAPS exclusively for text that must appear in the final image (e.g., "qSOFA", "30 mL/kg"). Use lowercase for emphasis, spatial directions, and instructional language ("already crossed," "foreground," "left ring").

### Proven Positive Patterns

These formulas consistently produce A+ (>=96) images. Use them by default in every prompt.

1. **Label readability formula**: For every required text label, write: *"A large brass plaque bolted to [object] reads [LABEL] in bold block letters."* Vague phrasing like "stamped with" or bare "reads" produces small or garbled labels. The "bolted plaque + bold block letters" pattern forces Gemini to render text large and legible.

2. **Text allowlist fence**: Always end the prompt with: *"Visible text limited to: [comma-separated list of allowed labels]. No other text, no floating captions, no zone labels, no speech bubbles, no directional words anywhere in the image."* This prevents spurious text from leaking into the scene.

3. **Style opener**: Begin every prompt with: *"Detailed hand-drawn medical mnemonic illustration in warm ink-and-watercolor style, wide 16:9 format, every element large and silhouette-readable."*

4. **Reading path**: Include a reading path in the second sentence: *"The eye enters at [entrance], sweeps through [zones], climbs to [back], and returns."*

5. **Completed-state language**: For sequence/timing anchors, describe the completed state: *"has crossed the line"* not *"crossing,"* *"has swung open"* not *"opening."* Gemini defaults to active states.

6. **Multi-part verification phrase**: When a feature requires an exact count (e.g., three-headed dog), add: *"All three heads are clearly visible and separated."*

7. **Full-prompt regeneration over repair patches**: When fixing issues, rewrite the complete prompt with fixes embedded. Targeted repair instructions cause previously-working elements to be dropped during regeneration.

8. **External auditor, never self-grade**: The image generator (AG/Gemini) must NOT audit its own output. Self-grading inflates scores by 15-20 points. Claude audits externally against the anchor table.

### Prompt Length Rule
Shorter prompts score higher. Every sentence is a chance for Gemini to misinterpret. Target:
- **Single-anchor plates (plate_size=1)**: 150-250 words max for the director prompt.
- **Full-scene prompts (all anchors)**: 400-600 words max for prompt2.
- If a prompt exceeds these limits, cut description of the room/setting first, then cut secondary visual details. Never cut the core mnemonic hook or required labels.

### Spatial Term Rules
Use only these coarse spatial terms in prompts. Do NOT use compound positions.

| Use this | NOT this |
|----------|----------|
| LEFT | center-left, left-of-center |
| CENTER | dead center, exact center |
| RIGHT | center-right, right-of-center |
| FOREGROUND | foreground-left corner |
| BACKGROUND | far background left |
| TOP / ABOVE | upper-third |
| BOTTOM / BELOW | lower-third |

When a figure and its effect must occupy different zones, place them in separate coarse zones (e.g., "figure stands LEFT; the explosion fills the CENTER sky").

### Repair Loop Rules
The repair process is the most common source of prompt degradation. These rules are mandatory:

1. **Repairs must be SHORTER than or equal to the original prompt.** If a repair is longer, it will score worse. Cut failed details; do not add compensating detail.
2. **Never add micro-poses in repairs.** When an audit says "the figure's hands are wrong," the fix is to REMOVE the hand description, not to specify exact finger positions.
3. **Never add ground/surface contrast in repairs.** If the floor detail failed, drop it entirely. Let the mnemonic contrast live in the objects/flames/figures, not the background surfaces.
4. **Rewrite the ENTIRE director prompt on repair, using different visual strategies.** Do not append audit feedback or patch individual sentences — rewrite from scratch with the same mnemonic hook but simpler visual encoding.
5. **Maximum 5 repair iterations per plate.** If a plate has not passed after 5 attempts, the anchor's visual encoding strategy is wrong — redesign the hook, not the prompt wording.

## QA Threshold

Use `tools/visual_qa_pack.py` to create review packs from exported forge bundles.

For old bundles, use:

```powershell
python tools\visual_qa_pack.py "path\to\bundle.json" --output-root "Troubleshooting Prompts\_visual_qa_packs" --refresh-prompt-contract
```

Target score:

- pre-image structural audit: `>=85`
- final manual image audit: `>=96` (publishable quality)

If the failure would affect future topics, fix the prompt contract. If the failure is isolated to one image, use a targeted repair prompt.

## Gemini Image Audit Workflow

Each QA pack should include these files:

- `02_gemini_prompt_2_all_anchors.txt`: the prompt to generate or regenerate the image.
- `03_anchor_table.md`: the source of truth for what the image must contain.
- `07_gemini_image_audit_prompt.txt`: paste this into Gemini with the generated image to get a structured audit.
- `08_repair_or_regenerate_prompt_template.txt`: use this after the audit to repair only failed items or regenerate after a contract change.

Use Gemini as a visual auditor against our anchor table, not as a source of medical truth. If Gemini says an anchor is missing, too small, misspelled, or text-dependent, verify visually and decide whether it is a one-image repair or a repeatable prompt-contract issue.

Repair when:

- one to three labels are misspelled
- one anchor needs a clearer label or restored symbol
- the composition is otherwise strong

Regenerate when:

- more than two anchors are missing
- the scene ignores spatial hierarchy
- the image becomes an infographic or checklist
- formulas/numbers are wrong in a medically meaningful way
- the same failure would affect future topics
