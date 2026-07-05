---
name: provider-proxy-quota-check
description: Review AI provider proxy, quota, rate-limit, usage logging, and generation error handling changes in Mnemorized.
---

# Provider Proxy Quota Check

Use this when work touches `/api/anthropic/messages`, `/api/generate-image`, `/api/gemini/prompt-director`, `/api/elevenlabs/tts`, provider settings, rate limiting, usage logging, quotas, plans, or API-key handling.

For quota reservation mechanics and provider transport quirks (dual Gemini auth methods, ElevenLabs status passthrough, evidence-grounding system-prompt injection), load `mnemorized-backend-map` first.

## Workflow

1. Identify the provider path: Anthropic messages, image generation, config/public, account summary, rate limit, or usage event persistence.
2. Trace:
   - client payload construction
   - FastAPI validation
   - auth/quota/rate-limit gates
   - provider request
   - usage logging
   - error response returned to the UI
3. Check:
   - real keys are read only from server-side environment
   - quota failure happens before paid provider calls
   - quota reservation is released on every provider failure/timeout branch (the reservation is optimistic, in-process, 60s TTL)
   - provider errors are visible and do not look like generated content
   - quota exhaustion still returns 402 with the `quota_exceeded` body the frontend parses
   - logs avoid storing secrets
   - local missing-key mode is clear
   - a dev plan override in `backend/dev_data/plan_overrides.json` is not silently masking the behavior under test
4. Validate syntax with `python -m compileall backend`; provider-call validation requires real local or hosted keys.

## Avoid

- putting provider keys in frontend code
- broad retry loops that can burn API credits
- swallowing backend errors into generic UI success

