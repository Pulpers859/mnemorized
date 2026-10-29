"""Durable admission rehearsal. No credentials, network or live-spend authority."""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import sqlite3

MODEL = "claude-sonnet-4-6"
STAGES = ("stage1-clinical-context", "medical-contract-source-review",
          "stage2-story-script-compact", "visual-preflight-review-0")
INPUT_LIMIT = 30000
OUTPUT_LIMIT = 6144
# Standard/global USD microdollars per token, verified 2026-10-28. No caching/tools premiums.
RESERVATION = INPUT_LIMIT * 3 + OUTPUT_LIMIT * 15
COUNT_URL = "https://api.anthropic.com/v1/messages/count_tokens"
MESSAGE_URL = "https://api.anthropic.com/v1/messages"


class AdmissionError(ValueError):
    pass


def serialized(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def validate_request(body: dict, headers: dict) -> dict:
    """Return the final count payload, never dropping input-bearing content."""
    allowed = {"model", "max_tokens", "system", "messages", "temperature", "top_p", "tools", "tool_choice"}
    if set(body) - allowed or body.get("model") != MODEL:
        raise AdmissionError("Unknown model, billing feature or request field")
    if type(body.get("max_tokens")) is not int or not 1 <= body["max_tokens"] <= OUTPUT_LIMIT:
        raise AdmissionError("Output limit exceeded")
    if headers.get("anthropic-beta") or headers.get("anthropic-version", "2023-06-01") != "2023-06-01":
        raise AdmissionError("Unsupported beta or API version")
    if not isinstance(body.get("system"), str) or not body["system"].strip():
        raise AdmissionError("System instructions required")
    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        raise AdmissionError("Messages required")
    for message in messages:
        if (not isinstance(message, dict) or set(message) != {"role", "content"}
                or message["role"] not in {"user", "assistant"}):
            raise AdmissionError("Only plain text messages supported")
        content = message["content"]
        if isinstance(content, str):
            continue
        if (not isinstance(content, list) or not content or any(
                not isinstance(b, dict) or set(b) != {"type", "text"}
                or b["type"] != "text" or not isinstance(b["text"], str) for b in content)):
            raise AdmissionError("Media, cache and tool-result blocks are unsupported")
    tools = body.get("tools")
    if tools is not None:
        if (not isinstance(tools, list) or len(tools) != 1 or not isinstance(tools[0], dict)
                or set(tools[0]) != {"name", "description", "strict", "input_schema"}
                or tools[0]["name"] != "submit_visual_preflight_review"
                or tools[0]["strict"] is not True or not isinstance(tools[0]["description"], str)
                or not isinstance(tools[0]["input_schema"], dict)):
            raise AdmissionError("Only the client preflight output tool is supported")
        if body.get("tool_choice") != {"type": "tool", "name": "submit_visual_preflight_review", "disable_parallel_tool_use": True}:
            raise AdmissionError("Unexpected tool choice")
    elif "tool_choice" in body:
        raise AdmissionError("Tool choice without tool")
    return {k: v for k, v in body.items() if k not in {"max_tokens", "temperature", "top_p"}}


class BudgetLedger:
    """Never releases reservations, including timeouts or unknown outcomes.

    Immutable policy is stored in the same SQLite file. This is an estimated
    reservation ceiling, NOT a guaranteed provider charge limit. No live mode.
    """
    def __init__(self, path: Path):
        self.path = Path(path).resolve()
        if not self.path.is_file():
            raise AdmissionError("Rehearsal ledger must be explicitly initialized")
        with closing(self._connect()) as db:
            row = db.execute("SELECT policy FROM pilot WHERE id=1").fetchone()
            if row is None:
                raise AdmissionError("Missing rehearsal policy")
            self.policy = json.loads(row[0])
            self._validate_policy(self.policy)

    @staticmethod
    def _validate_policy(policy: dict) -> None:
        if (not isinstance(policy, dict) or set(policy) != {"version", "mode", "pilot_id", "topic_ids", "cap_microdollars", "max_calls"}
                or policy["version"] != 1 or policy["mode"] != "dry_run"
                or not isinstance(policy["pilot_id"], str) or not re.fullmatch(r"[a-z0-9-]{1,64}", policy["pilot_id"])
                or type(policy["cap_microdollars"]) is not int or not 0 < policy["cap_microdollars"] <= 6000000
                or type(policy["max_calls"]) is not int or not 0 < policy["max_calls"] <= 24
                or not isinstance(policy["topic_ids"], list) or not 1 <= len(policy["topic_ids"]) <= 3
                or any(not isinstance(t, str) or not re.fullmatch(r"[a-z0-9-]{1,64}", t) for t in policy["topic_ids"])
                or len(set(policy["topic_ids"])) != len(policy["topic_ids"])):
            raise AdmissionError("Invalid rehearsal policy; live mode is not implemented")

    @classmethod
    def create(cls, path: Path, policy: dict) -> BudgetLedger:
        cls._validate_policy(policy)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation prevents accidentally resetting an exhausted pilot.
        with path.open("xb"):
            pass
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("CREATE TABLE pilot(id INTEGER PRIMARY KEY CHECK(id=1), policy TEXT NOT NULL)")
            db.execute("INSERT INTO pilot VALUES(1,?)", (serialized(policy),))
            db.execute("CREATE TABLE reservations(request_id TEXT PRIMARY KEY, topic TEXT NOT NULL, arm TEXT NOT NULL, stage TEXT NOT NULL, body_sha256 TEXT NOT NULL, estimated_input INTEGER NOT NULL, reserved_microdollars INTEGER NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(topic,arm,stage))")
            for action in ("UPDATE", "DELETE"):
                db.execute(f"CREATE TRIGGER no_{action.lower()} BEFORE {action} ON reservations BEGIN SELECT RAISE(ABORT, 'reservations are immutable'); END")
        return cls(path)

    def _connect(self):
        return sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, timeout=10)

    def precheck(self, topic: str, arm: str, stage: str) -> None:
        """Avoid counting obviously blocked requests; reserve still rechecks atomically."""
        if topic not in self.policy["topic_ids"] or arm not in {"baseline", "candidate"} or stage not in STAGES:
            raise AdmissionError("Unknown topic, arm or stage")
        with closing(self._connect()) as db:
            count, total = db.execute("SELECT COUNT(*), COALESCE(SUM(reserved_microdollars),0) FROM reservations").fetchone()
            arm_count = db.execute("SELECT COUNT(*) FROM reservations WHERE topic=? AND arm=?", (topic, arm)).fetchone()[0]
        if count >= self.policy["max_calls"] or total + RESERVATION > self.policy["cap_microdollars"]:
            raise AdmissionError("Rehearsal ceiling exhausted")
        if arm_count >= len(STAGES) or STAGES[arm_count] != stage:
            raise AdmissionError("Stage repeated, skipped or arm exhausted")

    def reserve(self, request_id: str, topic: str, arm: str, stage: str,
                body: dict, estimated_input: int, headers: dict) -> dict:
        validate_request(body, headers)
        if (topic not in self.policy["topic_ids"] or arm not in {"baseline", "candidate"}
                or stage not in STAGES or not isinstance(request_id, str) or not request_id):
            raise AdmissionError("Unknown topic, arm, stage or request")
        if type(estimated_input) is not int or not 0 <= estimated_input <= INPUT_LIMIT:
            raise AdmissionError("Invalid or excessive final input estimate")
        body_hash = hashlib.sha256(serialized(body).encode()).hexdigest()
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            current_policy = db.execute("SELECT policy FROM pilot WHERE id=1").fetchone()[0]
            if current_policy != serialized(self.policy):
                raise AdmissionError("Rehearsal policy changed")
            count, total = db.execute("SELECT COUNT(*), COALESCE(SUM(reserved_microdollars),0) FROM reservations").fetchone()
            arm_count = db.execute("SELECT COUNT(*) FROM reservations WHERE topic=? AND arm=?", (topic, arm)).fetchone()[0]
            if count >= self.policy["max_calls"] or total + RESERVATION > self.policy["cap_microdollars"]:
                raise AdmissionError("Rehearsal request or reservation ceiling exhausted")
            if arm_count >= len(STAGES) or STAGES[arm_count] != stage:
                raise AdmissionError("Stage repeated, skipped or arm exhausted")
            try:
                db.execute("INSERT INTO reservations(request_id,topic,arm,stage,body_sha256,estimated_input,reserved_microdollars) VALUES(?,?,?,?,?,?,?)",
                           (request_id, topic, arm, stage, body_hash, estimated_input, RESERVATION))
            except sqlite3.IntegrityError as exc:
                raise AdmissionError("Duplicate request; reservation was not released") from exc
        return {"mode": "dry_run", "live_authorized": False, "request_id": request_id,
                "body_sha256": body_hash, "estimated_input_tokens": estimated_input,
                "reserved_microdollars": RESERVATION, "total_reserved_microdollars": total + RESERVATION,
                "requests_reserved": count + 1, "financial_guarantee": False}

    def report(self) -> dict:
        with closing(self._connect()) as db:
            count, total = db.execute("SELECT COUNT(*), COALESCE(SUM(reserved_microdollars),0) FROM reservations").fetchone()
        return {"policy": self.policy, "requests_reserved": count, "reserved_microdollars": total,
                "live_authorized": False, "financial_guarantee": False}
