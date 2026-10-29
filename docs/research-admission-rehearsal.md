# Research Admission Rehearsal

Version1remains **dry-run safety infrastructure**, not a hard financial cap.
Do not remove its409response. A separately initialized and reviewed version2
bounded-live mode was added2026-10-29; it does not convert or reset a v1ledger.
The$6task-wide ceiling and six AG renders are unchanged. Version2also includes
retrieval embeddings conservatively within that same dollar ceiling.

## Behavior

- Normal server behavior is unchanged when RESEARCH_BUDGET_PATH is unset.
- A first-attempt profile request without that server guard is rejected409before
  any provider call, even if keys are configured.
- An isolated development server with that setting requires an existing SQLite
  ledger under Troubleshooting Prompts. Initialize it explicitly with
  backend.app.research_budget.BudgetLedger.create(path, policy); existing files
  cannot be overwritten. Do not rotate ledgers to evade a task-wide allowance.
- Policy keys: version1, mode dry_run, pilot_id, one to three distinct topic_ids,
  cap_microdollars<=6000000, max_calls<=24. Freeze actual topic IDs with the pilot;
  rehearsal fixtures are not a novelty review or authorization for generation.
- All Anthropic messages on that server pass through the rehearsal branch, not
  merely requests carrying an opt-in header. Missing profile headers fail closed.
  Other Gemini/image/TTS/probe lanes are disabled. Use a separate loopback server;
  do not alter production environment settings.
- Count the FINAL request after source evidence, active Constitution and client
  tool schemas are injected. Allow only Sonnet4.6 standard/global, plain text and
  the existing strict client preflight output tool. Advisor, beta features, caching,
  media, server tools, unknown fields/endpoints and excess output fail closed.
- Successful counting reserves182160USD microdollars atomically, conservatively
  using30000input+6144output at the pinned rates. The count must be<=30000.
  Four ordered stages per topic/arm,24total maximum. Never release reservations,
  including uncertain outcomes. SQLite transactions protect concurrent workers;
  reopening preserves reservations and a changed policy is rejected.
- Return409with a receipt, exact final body hash, input estimate and totals.
  **Never forward to the billable Messages endpoint.** Failed token counting
  creates no reservation because no billable generation was dispatched.

Token counting is free but estimated. Live embeddings and cassette replay are
blocked in rehearsal, including embedding calls through medical endpoints. Use
an offline captured-source harness for grounded-body rehearsal. Pre-admission
rejects invalid/exhausted arms before counting, then reservation rechecks atomically.
Offline tests mock all transports; passing them is not live provider verification.

## Forge Profile

The existing browser runner accepts --first-attempt-arm baseline|candidate plus
--first-attempt-topic-id ID; it forbids recovery/repair/expert flags in that mode.
Alternatively configure window.MnemorizedFirstAttempt once before starting Forge.
Topic/source scope must request exactly eight anchors. No retry, micro-repair,
clinical repair, visual repair or escalation is permitted. A page refresh is not
a new allowance; server ledger stage/count limits remain authoritative.

The profile exports its arm, topic, blocked state and ordered requests. Candidate
differs only by omitting the body-system setting row from the story metaphor list.
The normal default list, medical checks and image compiler are unchanged.

## Remaining Live Gate

The token estimate is still NOT a financial bound. Version2uses a different proof:
before each Anthropic dispatch, verify the provider Models API still reports the
pinned Sonnet4.6maximum input of1,000,000tokens. The request explicitly pins
service_tier=standard_only,inference_geo=global; no caching, beta, media, server
tools, advisor or other paid features are allowed. Standard/global rates across
the full window are$3/Minput and$15/Moutput, rechecked2026-10-29.

Reserve1,000,000*3+6,144*15=3,092,160USD microdollars BEFORE forwarding, not the
30,000-token estimate. In one SQLite transaction require existing settled charges
plus all outstanding full reservations plus this new maximum to be<=6,000,000.
Only one provider request may be outstanding. After exact HTTP200, validate model,
unique response identity, request body hash, token ranges, all billable fields
and standard/global usage; append a settlement for the known actual charge.
Only its known unused allocation becomes available again. Never reclaim an
uncertain reservation after timeout, malformed response, error or process crash.
Any pending reservation halts further dispatch, including across restarts.

This is a bound under the provider's documented enforced input/output limits and
listed standard/global tariff, not a promise against provider billing bugs or
other applications' account spend. Unknown settings/bounds block dispatch.
The conservative full-window reserve may block the cohort before24calls even
when a smaller estimated counter would fit. Preserve those blocked denominators.

Text-embedding-3-small uses a single string input only (no input arrays), max8192
tokens at$0.02/M. Reserve164microdollars per call, rounded UP, within the SAME
ledger; retain that full amount even after valid success. Max100embedding calls.
Any unknown embedding outcome remains pending and halts the pilot too. Other
generation/probe lanes and replay remain disabled. No retries or redirects.

Version2policy retains the same six keys as v1with version2/mode bounded_live.
Initialize through LiveBudgetLedger.create only after reviewed code, calibration
and prospective freeze prerequisites are met. No ledger rotation or reset to
evade the task cap. Body, metadata, receipt and response packets are preserved
under the ledger's provider_packets directory without API-key headers.

Primary references:
[context limits](https://platform.claude.com/docs/en/build-with-claude/context-windows),
[pricing](https://platform.claude.com/docs/en/about-claude/pricing),
[service tiers](https://platform.claude.com/docs/en/api/service-tiers),
[embedding limits](https://developers.openai.com/api/reference/resources/embeddings/methods/create),
[embedding price](https://developers.openai.com/api/docs/models/text-embedding-3-small).
