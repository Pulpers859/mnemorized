---
name: antigravity-image-loop
description: Operate the Google Antigravity image-generation loop — agentapi bridge discovery, prompt-file mechanics, audit/repair cycle, run-packet layout, and pass criteria. Use for visual mnemonic plate generation, AG stress tests, or any task involving ANTIGRAVITY.md workflows.
---

# Antigravity Image Loop

Operational checklist. Sources of truth: `ANTIGRAVITY.md` (workflow), `docs/gemini-constitution.txt` (prompt repair + session cost protocol), `docs/visual-mnemonic-prompt-contract.md` (quality + IP boundary). This skill is the summary; consult those files via offset reads for detail.

## Bridge mechanics

- Use `tools/Invoke-AntigravityAgentApi.ps1` (wraps `agentapi.bat`). It auto-discovers the running `language_server.exe`, reads the CSRF token from its `--csrf_token` command-line arg, and uses the **highest** listening TCP port. Port and token change on every Antigravity restart — never reuse stale values.
- Use the chat lane (`new-conversation` / `send-message`). **Never** use raw `StartCascade`/`SendUserCascadeMessage` RPC for image runs — that routes to AG's coding-agent lane and wastes the run inspecting the repo.
- Multiline prompts MUST be passed as a file (`-PassPromptFileAsAtPath`) — inline multiline text sends only the first line.

## The loop

1. Write `01_image_prompt.txt` (from a real Forge bundle export — hand-authored prompts must be labeled `renderer_experiment`).
2. AG generates and saves the image. AG does not audit itself.
3. Audit externally against `02_audit_prompt.txt`.
4. If `OVERALL_SCORE < 96` or `DECISION != PASS`: repair via `send-message`. Repairs rewrite the entire prompt, must be shorter or equal, never add micro-poses. Max 5 attempts total, then redesign the hook instead of iterating.
5. Save `antigravity_result.md` (pass) or `antigravity_blocked.md` (blocked).
6. `/compact` after every AG round-trip (session cost protocol).

## Run packets

- Location: `Troubleshooting Prompts/<topic>_<date>/plate_N/` with `01_image_prompt.txt`, `02_audit_prompt.txt`, `03_repair_rules.txt` in; `antigravity_iterN*.png`, `antigravity_audit_iterN.md`, result/blocked file out.
- The whole `Troubleshooting Prompts/` tree is **gitignored** — it is ephemeral scratch, not durable history. Anything worth keeping must be summarized into committed docs.

## Pass criteria

- A clean pass claim requires the saved audit literally stating `OVERALL_SCORE >= 96` and `DECISION: PASS`.
- Text-heavy results must be marked `PASS_WITH_TEXT_RISK` or `NEEDS_CONSTITUTION_REGEN` — never reported as a clean pass.

## Hard boundaries

- AG must not touch `backend/`, `frontend/`, `tools/`, `tests/`, `render.yaml`, or `.env`; must not call paid backend provider endpoints without explicit spend approval; must not commit or push.
- Never copy proprietary visual vocabulary (Sketchy/Pixorize scenes, characters, symbol mappings) — reusable design principles only, per the prompt contract.
