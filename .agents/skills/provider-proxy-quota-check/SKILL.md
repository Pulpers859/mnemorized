---
name: provider-proxy-quota-check
description: Review AI provider proxy, quota, rate-limit, usage logging, and generation error handling changes in Mnemorized.
---

# Provider Proxy Quota Check

Use this when work touches `/api/anthropic/messages`, `/api/generate-image`, provider settings, rate limiting, usage logging, quotas, plans, or API-key handling.

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
   - provider errors are visible and do not look like generated content
   - logs avoid storing secrets
   - local missing-key mode is clear
4. Validate syntax with `python -m compileall backend`; provider-call validation requires real local or hosted keys.

## Avoid

- putting provider keys in frontend code
- broad retry loops that can burn API credits
- swallowing backend errors into generic UI success

