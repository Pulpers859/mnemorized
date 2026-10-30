# Scene Generation Contract

The six failed attempts in the 2026-10-29 pilot are retained, not repaired or
rescored. Their failures led to these production changes:

- Clinical extraction supplies source-grounded teaching units, not an upstream
  room/prop plan. Scene writing owns the visual associations.
- The scene writer must complete one strict `submit_memory_palace` tool call.
  Its fixed slot inventory preserves the requested anchor count. Each slot has
  its own hook, narration, drawable visual, clinical fact and review line.
- Shared limits live in `forge-story-contract.js`: VISUAL target24/max34;
  opening target20-35/max60. These are unchanged hard ceilings, not relaxed
  criteria. Grammar patterns bound generated drawing fields; the client checks
  them again. Clinical facts are not clipped to fit a drawing budget.
- The decoder rejects partial, truncated, mixed, wrong-tool or changed-inventory
  output. Existing XML imports remain readable. Ordinary-mode XML format repair
  rejects truncation and protects room/learning text and anchor inventory before
  accepting a visual edit. Inline field-label words no longer replace narration.
- Clinical reviewer target/field/quote triples are enumerated from the exact
  current lesson, and citation pairs come from actual retrieved metadata.
  Drawing-label and mnemonic-consistency complaints belong in visual/association
  review when clinical text is supported. Invalid old reviews remain invalid;
  there is no automatic rerouting, unsupported clearance or medical gap filling.

Anthropic documents limited regex patterns, strict tools and primitive enums;
`maxLength`, `maxItems` and most numeric constraints are unsupported. The free
counter rejected ranged repetition of a variable-length word group despite the
broad documented quantifier support. Flat optional groups exhibited pathological
negative-case backtracking offline; a single60-word nested chain exceeded the
provider's50-level ceiling. Prefix chains in at-most30-level chunks preserve the
same exact word bound, reject long inputs quickly and were admitted in the full
eight-unit scene request by the free counter. See [official structured-output limitations](https://platform.claude.com/docs/en/build-with-claude/structured-outputs#json-schema-limitations),
checked2026-10-29. Counter admission is not paid generation validation.
Mechanical conformance is not clinical truth, coherent recall
or pixel quality. Source review and independent image audits remain mandatory.

Regression tests execute actual JS modules, including excerpts from failed
outputs. Nonclinical fixtures test code only; they are not app medical stress
tests. Real browser checks at1440/390px verify script loading and layout, with
all POSTs blocked. Neither those checks nor pytest prove an image-quality pass.
