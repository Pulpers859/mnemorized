# Guided Video Pipeline

This document describes the first production-safe foundation for turning a generated memory palace image into a narrated guided lesson.

## Current Scope

The app currently supports five stages:

1. Anchor coordinate mapping on the generated palace image.
2. ElevenLabs Studio narration handoff via copy/download script.
3. Local pan/highlight preview using estimated timing or uploaded/generated audio.
4. Backend-only ElevenLabs TTS endpoint (`POST /api/elevenlabs/tts`) with auth, rate limiting, quota enforcement, and usage logging. The API key never reaches the browser.
5. Supabase Storage for generated/uploaded audio. Audio files are uploaded to the `palace-audio` bucket, scoped per-user and per-palace. Saved palaces with `storage: "supabase"` auto-restore audio on load.

## User Workflow

1. Forge the palace script and image.
2. In `Guided Lesson Builder`, click `Build Plan`.
3. Click `Generate Audio` to create narration via the backend ElevenLabs proxy, **or** use the manual path: `Copy ElevenLabs Script` → paste into ElevenLabs Studio → export → upload.
4. Click anchors or edit normalized `x/y` coordinates until the highlight lands on each visual mnemonic.
5. Click `Play Preview`.
6. Save the palace or export the bundle when the coordinate/timing metadata is ready.

## Data Model

Saved palace versions now include `generation_outputs.guided_video`:

```json
{
  "version": 1,
  "provider_workflow": "manual-elevenlabs-studio",
  "anchor_coords": [
    {
      "n": 1,
      "x": 0.16,
      "y": 0.22,
      "found": true,
      "note": "",
      "encodes": "Clinical fact",
      "visual": "Visual anchor description"
    }
  ],
  "narration_segments": [
    {
      "n": 1,
      "start_seconds": 0,
      "duration_seconds": 8,
      "end_seconds": 8,
      "narration": "Spoken narration",
      "visual": "Visual anchor",
      "anchor": "Clinical fact",
      "hook": "Mnemonic strategy"
    }
  ],
  "audio": {
    "name": "exported-audio.mp3",
    "duration_seconds": 123,
    "storage": "supabase",
    "storage_path": "user-uuid/palace-uuid/exported-audio.mp3"
  }
}
```

Coordinates are normalized from `0.0` to `1.0`, so they survive image resizing.

## Important Boundaries

- Generated or uploaded audio is automatically persisted to Supabase Storage when a palace is saved. On load, audio is streamed back through the backend proxy — no manual re-upload needed.
- If the palace has not been saved yet (no `palace_id`), audio stays in browser memory until the first save; the next load will restore it from storage.
- The manual Studio copy/download path is preserved as a fallback for cost control and QA.
- Audio files are stored at `{user_id}/{palace_id}/{filename}` in the `palace-audio` bucket, enforcing per-user isolation via Supabase RLS.

## Next Stages

1. Rendered video export, likely via a backend worker or local CLI pipeline rather than browser-only canvas capture.
2. Image-audit-aware coordinate assist, where vision proposes anchor coordinates and the user confirms them.
