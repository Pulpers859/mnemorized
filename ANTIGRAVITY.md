# Antigravity Visual QA Workflow For Mnemorized

This file defines the safe default workflow for using Google Antigravity with Mnemorized.

Antigravity's primary role in this repo is **visual QA lab**, not app integrator. Use it for image generation, image-audit loops, prompt repair experiments, and visual artifact reports. Codex or Claude should integrate durable findings into source code, tests, and commits unless Patrick explicitly asks Antigravity to make code changes.

## Source Of Truth

- Active repo: `C:\Dev\Mnemorized`
- General repo rules: `AGENTS.md`
- Medical visual prompt contract: `docs/visual-mnemonic-prompt-contract.md`
- Visual experiment workspace: `Troubleshooting Prompts/`

Do not use the stale OneDrive/Desktop app copy for app work.

## Default Role

Use Antigravity for:

- generating trial images from Mnemorized prompt packs
- saving generated image artifacts in the relevant troubleshooting folder
- applying repair/regeneration prompts supplied by Codex or Claude
- writing concise generation notes in the relevant troubleshooting folder
- writing concise findings that Codex/Claude can fold back into the app

Do not let Antigravity self-grade the final image quality. Its self-audits have
been observed to inflate scores. Codex or Claude should read the generated image
externally, audit against the saved rubric, assign the score, and decide whether
to repair or regenerate.

## Codex Or Claude As Prompt Architect

Codex and Claude can occupy the same non-visual control seat in this workflow.
Whichever agent is active should own the prompt architecture, anchor-table review,
external audit judgment, Constitution updates, source-code integration, and final
commit/push. Antigravity remains the image-generation and visual-artifact lab.

Do not duplicate effort by having Codex and Claude both rewrite the same prompt
pack at the same time. The active architect should leave a compact run note in the
topic folder so the next agent can continue from saved artifacts rather than
restarting the loop.

## Antigravity Automation Lanes

There are two distinct programmatic control lanes. Use the correct one.

### Path A: `agentapi.bat` Chat/Image Lane

This is the path Claude Code used successfully for image-generation
troubleshooting. Prefer this path for Codex too when command execution is
available.

Binary:

```text
C:\Users\PATRIC~1\.gemini\antigravity\bin\agentapi.bat
```

Wrapper target:

```text
C:\Users\Patrick's Computer\AppData\Local\Programs\antigravity\resources\bin\language_server.exe agentapi <subcommand>
```

Useful commands:

```powershell
& "C:\Users\PATRIC~1\.gemini\antigravity\bin\agentapi.bat" new-conversation --model=pro --title="COPD Plate 4" "<prompt text or @file>"
& "C:\Users\PATRIC~1\.gemini\antigravity\bin\agentapi.bat" send-message <conversation_id> "<follow-up message or @file>"
& "C:\Users\PATRIC~1\.gemini\antigravity\bin\agentapi.bat" get-conversation-metadata <conversation_id>
```

Repo helper:

```powershell
.\tools\Invoke-AntigravityAgentApi.ps1 -Command NewConversation -Title "COPD Plate 4" -PromptFile "C:\Dev\Mnemorized\Troubleshooting Prompts\...\ag_task.txt"
.\tools\Invoke-AntigravityAgentApi.ps1 -Command SendMessage -ConversationId <conversation_id> -PromptFile "C:\Dev\Mnemorized\Troubleshooting Prompts\...\repair.txt"
.\tools\Invoke-AntigravityAgentApi.ps1 -Command Metadata -ConversationId <conversation_id>
```

When using multiline task files, pass them as `@file` references so Antigravity
reads the whole file:

```powershell
.\tools\Invoke-AntigravityAgentApi.ps1 -Command NewConversation -Title "NIHSS Iter1" -PromptFile "C:\Dev\Mnemorized\Troubleshooting Prompts\...\ag_task.md" -PassPromptFileAsAtPath
.\tools\Invoke-AntigravityAgentApi.ps1 -Command SendMessage -ConversationId <conversation_id> -PromptFile "C:\Dev\Mnemorized\Troubleshooting Prompts\...\repair.md" -PassPromptFileAsAtPath
```

Without `-PassPromptFileAsAtPath`, a multiline prompt may arrive as only the
first line and Antigravity will not execute the intended image task.

The helper detects the running `language_server.exe` process, sets
`ANTIGRAVITY_LS_ADDRESS`, `ANTIGRAVITY_CSRF_TOKEN`, and
`ANTIGRAVITY_PROJECT_ID` for the child process, then invokes `agentapi.bat`.

Required environment variables, which may change after each Antigravity restart:

```text
ANTIGRAVITY_LS_ADDRESS=127.0.0.1:<https_port>
ANTIGRAVITY_CSRF_TOKEN=<csrf token from language_server.exe command line>
ANTIGRAVITY_PROJECT_ID=79655949-1be7-444b-817e-c0ecd5768c5c
```

Fresh-launch discovery on Windows:

```powershell
tasklist | findstr language_server
netstat -ano | findstr <PID>
wmic process where "processid=<PID>" get CommandLine
```

Use the higher `LISTENING` port from `netstat` as the HTTPS port. Extract the
CSRF token from the language-server command line's `--csrf_token` value.

Expected automation loop:

1. Codex/Claude reads the anchor table and
   `docs/visual-mnemonic-prompt-contract.md`.
2. Codex/Claude writes the generation prompt to `01_image_prompt.txt`.
3. Codex/Claude writes a task file for Antigravity that says:
   - generate/save the image
   - do not audit
   - do not score
   - do not edit app source
4. Codex/Claude calls `agentapi.bat new-conversation --model=pro --title=... @task_file`,
   or uses the repo helper with `-PassPromptFileAsAtPath`.
5. Codex/Claude polls the troubleshooting folder for the output image.
6. Codex/Claude reads the generated image and audits against
   `02_audit_prompt.txt` or the generated audit rubric.
7. If `OVERALL_SCORE < 96` or `DECISION != PASS`, Codex/Claude writes a repair
   or regeneration instruction and sends it with `agentapi.bat send-message`.
8. Repeat up to 5 attempts, then save `antigravity_result.md` or
   `antigravity_blocked.md`.

### Path B: Raw RPC Coding-Agent Lane

Codex can reach Antigravity's local RPC service when it is running. Verified
calls include `GetStandaloneDir`, `StartCascade`, `SendUserCascadeMessage`,
`HandleCascadeUserInteraction`, `CancelCascadeInvocation`, and
`ForceStopCascadeTree`.

When using raw RPC, `SendUserCascadeMessage` needs an explicit model config:

```json
{
  "cascadeConfig": {
    "plannerConfig": {
      "requestedModel": {
        "model": "MODEL_PLACEHOLDER_M20"
      }
    }
  }
}
```

`MODEL_PLACEHOLDER_M20` was observed as Antigravity's `Gemini 3.5 Flash
(Medium)` model on Patrick's machine.

Do not use raw `StartCascade` / `SendUserCascadeMessage` for image-generation
runs. It opens Antigravity's coding-agent lane, not the chat/image lane. In a
Codex test run, the agent accepted the visual QA prompt but drifted into repo
startup, git inspection, compile/test validation, and source reading instead of
generating `antigravity_iter1.png`.

If the visible Antigravity window is targetable through browser/computer control,
prefer controlling the actual UI image workflow over the raw coding-cascade RPC.
If the visible window is not targetable, use the Gemini App/browser manual paste
workflow or ask Patrick to run the Antigravity prompt from the visible UI, then
audit the saved artifacts.

Do not use Antigravity by default for:

- backend/provider proxy changes
- Supabase/auth/quota/persistence changes
- Render/env/secrets work
- commits or pushes
- broad refactors
- editing `frontend/pages/forge.html`

## Hard Boundaries

- Do not modify `backend/`, `frontend/`, `tools/`, `tests/`, `render.yaml`, `.env`, or secret/config files unless Patrick explicitly asks in the current prompt.
- Do not call Mnemorized backend provider endpoints for image generation unless Patrick explicitly approves API spend.
- Do not read unrelated private folders.
- Do not use patient-identifying information.
- Do not copy proprietary Sketchy/Pixorize scenes, characters, symbols, layouts, or fact-to-symbol mappings. Reusable design principles are allowed; copying visual vocabulary is not.
- Save generated images and audit notes only under `Troubleshooting Prompts/` unless instructed otherwise.

## Visual QA Passing Standard

Each image plate must pass:

- `OVERALL_SCORE >= 96`
- `DECISION: PASS`

Use the audit format from the plate's `02_audit_prompt.txt` or generated QA pack. Do not invent a looser scoring system.

For full-topic troubleshooting runs, save a complete run packet before reporting completion:

- original Forge/image prompt
- anchor table and narration/script
- every repair/regeneration prompt
- every generated image or screenshot that can be recovered
- final audit rubric with score breakdown
- explicit caveats, including whether the canonical Gemini Constitution was used

If the image is useful but violates the Constitution text budget, mark it `PASS_WITH_TEXT_RISK` or `NEEDS_CONSTITUTION_REGEN`; do not call it a clean `PASS`.

## Forge-First Requirement For Medical Stress Tests

When Patrick asks to troubleshoot prompt generation for a medical topic, do not
invent a small custom prompt and call that a stress test. The default must be the
real product path:

1. Run the topic through Mnemorized Forge.
2. Let the Medical Quality Gate run when backend auth/retrieval is available.
3. Check that retrieved citations match the topic. If they are absent or
   unrelated, stop and document the retrieval/ingestion gap.
4. Export the Forge bundle (`*_bundle.json`).
5. Build a QA pack with `tools/visual_qa_pack.py`.
6. Send the QA pack prompt to Antigravity for image generation.
7. Codex/Claude externally audits the image against the Forge anchor table,
   narration, clinical encodes, citations, and `docs/gemini-constitution.txt`.

Synthetic prompts are allowed only for narrow renderer probes. They are not
board-study validation, not source-grounded validation, and not catalog-quality
validation. Label them as `renderer_experiment` so future agents do not confuse
them with Forge results.

## Plate Folder Convention

For a manual plate folder such as:

```text
Troubleshooting Prompts\...\plate_N\manual_retry
```

Important: in Mnemorized, a `plate` is a focused render of one to three anchors
inside the same coherent memory-palace room. It is not a segmented grid, tiled
storyboard, bay-by-bay checklist, or infographic layout. Grid/bay layouts should
be rare exceptions. If a generated prompt turns a palace into panels, treat that
as a prompt failure unless the source scene itself intentionally requires that
metaphor and Patrick has accepted the tradeoff.

Expected inputs:

- `01_image_prompt.txt`: paste into image generation.
- `02_audit_prompt.txt`: use to audit the generated image.
- `03_repair_rules.txt`: use only after an audit returns `REPAIR` or `REGENERATE`.

Expected outputs:

- `antigravity_iter1.png`
- `antigravity_audit_iter1.md` written by Codex/Claude after externally reading the image
- `antigravity_iter2_repair.png` or `antigravity_iter2_regen.png` when needed
- `antigravity_result.md` when the plate passes
- `antigravity_blocked.md` if the plate cannot pass after bounded attempts

## Standard Loop

1. Read `AGENTS.md`, this file, and `docs/visual-mnemonic-prompt-contract.md`.
2. Work only in the requested topic/plate folder under `Troubleshooting Prompts/`.
3. Read `01_image_prompt.txt`.
4. Generate an image from that prompt using Antigravity's built-in image generator, preferably through `agentapi.bat new-conversation`.
5. Save the image as `antigravity_iter1.png`.
6. Codex/Claude reads `02_audit_prompt.txt`.
7. Codex/Claude audits the generated image against that rubric and the image itself.
8. Codex/Claude saves the audit as `antigravity_audit_iter1.md`.
9. If the score is `>=96` and decision is `PASS`, write `antigravity_result.md` and stop that plate.
10. If the audit says `REPAIR`, Codex/Claude reads `03_repair_rules.txt`, sends the repair instruction to Antigravity, saves the next image, and re-audits.
11. If the audit says `REGENERATE`, Codex/Claude sends `01_image_prompt.txt` plus the audit's `REGENERATION_PROMPT_CHANGE`, saves the next image, and re-audits.
12. Stop after 5 total attempts per plate. If still failing, write `antigravity_blocked.md` with the failure pattern and recommended prompt-level fix.

## What To Report Back

For each completed topic or plate set, write a summary markdown file in the topic troubleshooting folder with:

- plate status
- best score per plate
- final image filenames
- final audit filenames
- whether the run started from a real Forge bundle or was only a renderer experiment
- Medical Quality Gate citation status for full-topic medical runs
- prompt repair lessons
- systemic weaknesses that should be folded back into `docs/visual-mnemonic-prompt-contract.md` or the Forge pipeline
- whether the prompt used `docs/gemini-constitution.txt`, and if not, why not

Keep findings concise and evidence-backed. Do not claim an image passed unless the saved audit says `OVERALL_SCORE >= 96` and `DECISION: PASS`.

## Starter Prompt For Antigravity

Use this as the first prompt when starting a Mnemorized visual QA task:

```text
Read `AGENTS.md`, `ANTIGRAVITY.md`, and `docs/visual-mnemonic-prompt-contract.md`.

You are the Mnemorized Visual QA Lab. Work in `C:\Dev\Mnemorized`.

Your job is to generate visual mnemonic images from existing prompt packs, not to modify source code and not to score your own image quality.

Use only the requested folder under `Troubleshooting Prompts/`. Do not edit `backend/`, `frontend/`, `tools/`, `tests/`, `.env`, or deployment config. Do not commit or push. Do not call the Mnemorized backend/provider API for image generation unless I explicitly approve API spend.

For each requested plate folder:
1. Read `01_image_prompt.txt`.
2. Generate an image with Antigravity's built-in image generator.
3. Save it as `antigravity_iter1.png` in the same folder.
4. Stop and report the image filename. Do not audit, score, or declare pass/fail.
5. Wait for Codex/Claude to externally audit the image and send repair or regeneration instructions if needed.

When done, write a concise note with the generated image filename and any tool limitation encountered. Codex/Claude will write scores, final audit filenames, and systemic prompt lessons after external review.

Requested folder(s):
[PASTE THE TOPIC OR PLATE FOLDER PATHS HERE]
```
