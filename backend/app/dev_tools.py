from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PlanOverride:
    plan_code: str
    status: str


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_plan_overrides(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def read_plan_override(path: Path, user_id: str) -> PlanOverride | None:
    data = load_plan_overrides(path)
    row = data.get(user_id)
    if not row:
        return None
    return PlanOverride(
        plan_code=str(row.get("plan_code", "free")),
        status=str(row.get("status", "active")),
    )


def write_plan_override(path: Path, user_id: str, plan_code: str, status: str) -> None:
    data = load_plan_overrides(path)
    data[user_id] = {
        "plan_code": plan_code,
        "status": status,
    }
    _ensure_parent(path)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def clear_plan_override(path: Path, user_id: str) -> None:
    data = load_plan_overrides(path)
    if user_id in data:
        del data[user_id]
        _ensure_parent(path)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
