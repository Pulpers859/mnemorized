# Guided Video Pipeline

This document describes the first production-safe foundation for turning a generated memory palace image into a narrated guided lesson.

## Current Scope

The app currently supports the first three stages:

1. Anchor coordinate mapping on the generated palace image.
2. ElevenLabs Studio narration handoff via copy/download script.
3. Local pan/highlight preview using estimated timing or an uploaded ElevenLabs audio export.

This is intentionally a manual provider bridge. Forge does not store an ElevenLabs API key in the browser, does not call ElevenLabs yet, and does not save audio blobs into Supabase palace versions.

## User Workflow

1. Forge the palace script and image.
2. In `Guided Lesson Builder`, click `Build Plan`.
3. Click `Copy ElevenLabs Script` or `Download Script`.
4. Paste/import the script into ElevenLabs Studio.
5. Export the generated audio from ElevenLabs.
6. Upload that audio in Forge.
7. Click anchors or edit normalized `x/y` coordinates until the highlight lands on each visual mnemonic.
8. Click `Play Preview`.
9. Save the palace or export the bundle when the coordinate/timing metadata is ready.

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
    "storage": "local-browser-upload-only"
  }
}
```

Coordinates are normalized from `0.0` to `1.0`, so they survive image resizing.

## Important Boundaries

- Audio upload is local browser state only. Re-upload the file after loading a saved palace if you want audio playback.
- Supabase stores coordinate/timing metadata, not the audio file.
- The final API integration should use backend-only ElevenLabs credentials and a storage decision for generated audio.
- If provider API generation is added later, keep this manual Studio path as a fallback for cost control and QA.

## Next Stages

The next structurally sound additions are:

1. Backend-only ElevenLabs endpoint with quota/usage logging and provider error normalization.
2. Supabase Storage or private object storage for generated audio exports.
3. Rendered video export, likely via a backend worker or local CLI pipeline rather than browser-only canvas capture.
4. Image-audit-aware coordinate assist, where vision proposes anchor coordinates and the user confirms them.
