"""
Replay cassette system for dev-mode provider calls.

When FORGE_REPLAY header is present on a proxied request:
  - "record": call real API, save response to backend/replay/{slug}/{stage}.json
  - "replay": load saved response from disk, skip real API entirely

Cassettes are plain JSON files — editable, inspectable, deletable.
Completely inert in production (APP_ENV=production).
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger("mnemorized.replay")

REPLAY_DIR = Path(__file__).resolve().parents[1] / "replay"

HEADER_NAME = "x-forge-replay"
HEADER_TOPIC = "x-forge-replay-topic"
HEADER_STAGE = "x-forge-replay-stage"


def _slug(text: str) -> str:
    safe = re.sub(r"[^a-z0-9]+", "-", text.lower().strip())[:80].strip("-")
    return safe or hashlib.md5(text.encode()).hexdigest()[:12]


def _cassette_path(topic: str, stage: str) -> Path:
    return REPLAY_DIR / _slug(topic) / f"{_slug(stage)}.json"


def get_replay_mode(headers: dict[str, str] | Any) -> str | None:
    val = None
    if hasattr(headers, "get"):
        val = headers.get(HEADER_NAME)
    return val if val in ("record", "replay") else None


def get_replay_meta(headers: dict[str, str] | Any) -> tuple[str | None, str | None]:
    topic = headers.get(HEADER_TOPIC) if hasattr(headers, "get") else None
    stage = headers.get(HEADER_STAGE) if hasattr(headers, "get") else None
    return topic, stage


def load_cassette(topic: str, stage: str) -> dict[str, Any] | None:
    path = _cassette_path(topic, stage)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        logger.info("Replay cassette loaded: %s", path)
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Replay cassette unreadable (%s): %s", path, exc)
        return None


def save_cassette(topic: str, stage: str, response_body: dict[str, Any]) -> Path:
    path = _cassette_path(topic, stage)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(response_body, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Replay cassette saved: %s", path)
    return path


def list_cassettes() -> list[dict[str, Any]]:
    if not REPLAY_DIR.is_dir():
        return []
    results = []
    for topic_dir in sorted(REPLAY_DIR.iterdir()):
        if not topic_dir.is_dir():
            continue
        stages = sorted(f.stem for f in topic_dir.glob("*.json"))
        results.append({"topic_slug": topic_dir.name, "stages": stages})
    return results


def clear_cassette(topic: str, stage: str | None = None) -> int:
    count = 0
    if stage:
        path = _cassette_path(topic, stage)
        if path.is_file():
            path.unlink()
            count = 1
    else:
        topic_dir = REPLAY_DIR / _slug(topic)
        if topic_dir.is_dir():
            for f in topic_dir.glob("*.json"):
                f.unlink()
                count += 1
            try:
                topic_dir.rmdir()
            except OSError:
                pass
    return count
