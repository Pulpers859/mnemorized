# Research Admission Rehearsal

This is **dry-run safety infrastructure**, not an implemented hard financial cap.
There is no supported live mode. Do not remove its409response to run a benchmark.
The$6total Anthropic budget and six AG renders are unchanged.

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

A defensible billable-input bound or verified non-overshooting provider spending
control is still required. Headroom, integer accounting and blocking later calls
do not prevent a single underestimated request from exceeding a dollar promise.
Once resolved, independently review the transport changes before adding a live
dispatch mode. This rehearsal must not be silently relabeled safe for spending.
