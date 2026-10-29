"""Durable research admission and settlement; no credentials or network access."""
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
# Standard/global USD microdollars per token, verified 2026-10-29. No caching/tools premiums.
RESERVATION = INPUT_LIMIT * 3 + OUTPUT_LIMIT * 15
COUNT_URL = "https://api.anthropic.com/v1/messages/count_tokens"
MESSAGE_URL = "https://api.anthropic.com/v1/messages"
MODEL_URL = "https://api.anthropic.com/v1/models/" + MODEL
MODEL_INPUT_BOUND = 1000000
LIVE_RESERVATION = MODEL_INPUT_BOUND * 3 + OUTPUT_LIMIT * 15
EMBEDDING_RESERVATION = 164  # ceil(8192 tokens * $0.02/M), in microUSD.


class AdmissionError(ValueError):
    pass


def serialized(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def validate_request(body: dict, headers: dict) -> dict:
    """Return the final count payload, never dropping input-bearing content."""
    allowed = {"model", "max_tokens", "system", "messages", "temperature", "top_p", "tools", "tool_choice", "service_tier", "inference_geo"}
    if set(body) - allowed or body.get("model") != MODEL:
        raise AdmissionError("Unknown model, billing feature or request field")
    if type(body.get("max_tokens")) is not int or not 1 <= body["max_tokens"] <= OUTPUT_LIMIT:
        raise AdmissionError("Output limit exceeded")
    if headers.get("anthropic-beta") or headers.get("anthropic-version", "2023-06-01") != "2023-06-01":
        raise AdmissionError("Unsupported beta or API version")
    if body.get("service_tier", "standard_only") != "standard_only" or body.get("inference_geo", "global") != "global":
        raise AdmissionError("Only standard/global billing is allowed")
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
    return {k: v for k, v in body.items() if k not in {"max_tokens", "temperature", "top_p", "service_tier", "inference_geo"}}


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
            raise AdmissionError("Invalid rehearsal policy; bounded live requires a separate v2 ledger")

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


class LiveBudgetLedger(BudgetLedger):
    """Full model-bound reservation, then append-only verified-usage settlement.

    A pending reservation is never expired or reclaimed. Every provider dispatch
    is serialized durably, including embeddings. Pricing/model bounds are pinned.
    """
    @staticmethod
    def _validate_policy(policy: dict) -> None:
        if not isinstance(policy, dict) or policy.get("version") != 2 or policy.get("mode") != "bounded_live":
            raise AdmissionError("Invalid bounded-live policy")
        base = {**policy, "version": 1, "mode": "dry_run"}
        BudgetLedger._validate_policy(base)

    @classmethod
    def create(cls, path: Path, policy: dict):
        result = super().create(path, policy)
        with closing(result._connect()) as db, db:
            db.execute("ALTER TABLE reservations ADD COLUMN max_output INTEGER NOT NULL DEFAULT 6144")
            db.execute("ALTER TABLE reservations ADD COLUMN kind TEXT NOT NULL DEFAULT 'anthropic'")
            db.execute("CREATE TABLE settlements(request_id TEXT PRIMARY KEY REFERENCES reservations(request_id), actual_microdollars INTEGER NOT NULL, response_sha256 TEXT NOT NULL, usage TEXT NOT NULL, provider_id TEXT NOT NULL UNIQUE)")
            for action in ("UPDATE", "DELETE"):
                db.execute(f"CREATE TRIGGER no_settlement_{action.lower()} BEFORE {action} ON settlements BEGIN SELECT RAISE(ABORT, 'settlements are immutable'); END")
        return result

    def _state(self, db):
        liability, pending = db.execute("SELECT COALESCE(SUM(COALESCE(s.actual_microdollars,r.reserved_microdollars)),0), COALESCE(SUM(s.request_id IS NULL),0) FROM reservations r LEFT JOIN settlements s USING(request_id)").fetchone()
        return liability, pending

    def _check(self, db, topic=None, arm=None, stage=None, embedding=False):
        if db.execute("SELECT policy FROM pilot WHERE id=1").fetchone()[0] != serialized(self.policy):
            raise AdmissionError("Bounded-live policy changed")
        liability, pending = self._state(db)
        if pending:
            raise AdmissionError("Pending or uncertain provider request; pilot halted")
        reserve = EMBEDDING_RESERVATION if embedding else LIVE_RESERVATION
        if liability + reserve > self.policy["cap_microdollars"]:
            raise AdmissionError("Worst-case provider reservation exceeds remaining cap")
        if embedding:
            if db.execute("SELECT COUNT(*) FROM reservations WHERE kind='embedding'").fetchone()[0] >= 100:
                raise AdmissionError("Embedding request ceiling exhausted")
        else:
            if topic not in self.policy["topic_ids"] or arm not in {"baseline", "candidate"} or stage not in STAGES:
                raise AdmissionError("Unknown topic, arm or stage")
            if db.execute("SELECT COUNT(*) FROM reservations WHERE kind='anthropic'").fetchone()[0] >= self.policy["max_calls"]:
                raise AdmissionError("Anthropic request ceiling exhausted")
            count = db.execute("SELECT COUNT(*) FROM reservations WHERE kind='anthropic' AND topic=? AND arm=?", (topic, arm)).fetchone()[0]
            if count >= len(STAGES) or STAGES[count] != stage:
                raise AdmissionError("Stage repeated, skipped or exhausted")
        return liability

    def precheck(self, topic, arm, stage):
        with closing(self._connect()) as db:
            self._check(db, topic, arm, stage)

    def reserve(self, request_id, topic, arm, stage, body, estimated_input, headers):
        validate_request(body, headers)
        if body.get("service_tier") != "standard_only" or body.get("inference_geo") != "global":
            raise AdmissionError("Live requests require explicit standard/global billing pins")
        if not isinstance(request_id, str) or not request_id:
            raise AdmissionError("Request identity required")
        if type(estimated_input) is not int or not 0 <= estimated_input <= INPUT_LIMIT:
            raise AdmissionError("Invalid final input estimate")
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            liability = self._check(db, topic, arm, stage)
            body_hash = hashlib.sha256(serialized(body).encode()).hexdigest()
            db.execute("INSERT INTO reservations(request_id,topic,arm,stage,body_sha256,estimated_input,reserved_microdollars,max_output) VALUES(?,?,?,?,?,?,?,?)",
                       (request_id, topic, arm, stage, body_hash, estimated_input, LIVE_RESERVATION, body["max_tokens"]))
        return {"mode": "bounded_live", "request_id": request_id, "body_sha256": body_hash,
                "reserved_microdollars": LIVE_RESERVATION, "total_liability_microdollars": liability + LIVE_RESERVATION}

    @staticmethod
    def verify_model_metadata(metadata):
        if (not isinstance(metadata, dict) or metadata.get("id") != MODEL
                or type(metadata.get("max_input_tokens")) is not int
                or metadata["max_input_tokens"] != MODEL_INPUT_BOUND
                or type(metadata.get("max_tokens")) is not int or metadata["max_tokens"] < OUTPUT_LIMIT):
            raise AdmissionError("Provider model bound changed or is unknown")

    def _settle(self, request_id, body, response, kind):
        if not isinstance(response, dict) or not isinstance(response.get("usage"), dict):
            raise AdmissionError("Missing verified provider usage; reservation remains locked")
        usage = response["usage"]
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT body_sha256,max_output,kind,reserved_microdollars FROM reservations WHERE request_id=?", (request_id,)).fetchone()
            if not row or row[0] != hashlib.sha256(serialized(body).encode()).hexdigest() or row[2] != kind:
                raise AdmissionError("Settlement does not bind the dispatched request")
            if kind == "anthropic":
                allowed = {"input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "cache_creation", "output_tokens_details", "service_tier", "inference_geo", "speed", "server_tool_use"}
                if set(usage) - allowed or response.get("model") != MODEL:
                    raise AdmissionError("Unknown provider model or billable usage field")
                provider_id = response.get("id")
                if not isinstance(provider_id, str) or not provider_id.startswith("msg_"):
                    raise AdmissionError("Provider response identity missing")
                if not isinstance(usage.get("server_tool_use", {}), dict):
                    raise AdmissionError("Unknown server-tool usage")
                tool_usage = usage.get("server_tool_use", {})
                details = usage.get("output_tokens_details", {})
                if (set(tool_usage) - {"web_search_requests", "web_fetch_requests", "code_execution_requests"}
                        or not isinstance(details, dict) or set(details) - {"thinking_tokens"}
                        or any(type(v) is not int or v < 0 for v in details.values())):
                    raise AdmissionError("Unknown nested provider usage")
                for key, bound in (("input_tokens", MODEL_INPUT_BOUND), ("output_tokens", row[1])):
                    if type(usage.get(key)) is not int or not 0 <= usage[key] <= bound:
                        raise AdmissionError("Invalid provider token usage")
                if details.get("thinking_tokens", 0) > usage["output_tokens"]:
                    raise AdmissionError("Invalid thinking-token usage")
                if (any(usage.get(k, 0) != 0 for k in ("cache_creation_input_tokens", "cache_read_input_tokens"))
                        or usage.get("cache_creation", {}) not in ({}, {"ephemeral_5m_input_tokens": 0, "ephemeral_1h_input_tokens": 0})
                        or usage.get("service_tier", "standard") != "standard"
                        or usage.get("inference_geo", "global") != "global"
                        or usage.get("speed", "standard") != "standard"
                        or any(v != 0 for v in usage.get("server_tool_use", {}).values())):
                    raise AdmissionError("Unpriced provider usage; retain full reservation")
                actual = usage["input_tokens"] * 3 + usage["output_tokens"] * 15
            else:
                provider_id = "embedding:" + request_id
                if (response.get("model") != "text-embedding-3-small" or set(usage) != {"prompt_tokens", "total_tokens"}
                        or type(usage.get("prompt_tokens")) is not int
                        or not 0 <= usage["prompt_tokens"] <= 8192 or usage["total_tokens"] != usage["prompt_tokens"]):
                    raise AdmissionError("Invalid embedding usage")
                actual = EMBEDDING_RESERVATION
            if actual > row[3]:
                raise AdmissionError("Actual charge exceeds reservation")
            try:
                db.execute("INSERT INTO settlements VALUES(?,?,?,?,?)", (request_id, actual,
                    hashlib.sha256(serialized(response).encode()).hexdigest(), serialized(usage), provider_id))
            except sqlite3.IntegrityError as exc:
                raise AdmissionError("Duplicate settlement; no funds released") from exc
        return self.report()

    def settle(self, request_id, body, response):
        return self._settle(request_id, body, response, "anthropic")

    def reserve_embedding(self, request_id, body):
        if (not isinstance(request_id, str) or not request_id or body.get("model") != "text-embedding-3-small"
                or set(body) - {"model", "input", "dimensions"} or not isinstance(body.get("input"), str)
                or not body["input"].strip()):
            raise AdmissionError("Unknown embedding model or cost")
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            self._check(db, embedding=True)
            db.execute("INSERT INTO reservations(request_id,topic,arm,stage,body_sha256,estimated_input,reserved_microdollars,max_output,kind) VALUES(?,?,?,?,?,?,?,?,?)",
                (request_id, "embedding", "source", request_id, hashlib.sha256(serialized(body).encode()).hexdigest(), 8192, EMBEDDING_RESERVATION, 0, "embedding"))

    def settle_embedding(self, request_id, body, response):
        return self._settle(request_id, body, response, "embedding")

    def report(self):
        with closing(self._connect()) as db:
            liability, pending = self._state(db)
            count = db.execute("SELECT COUNT(*) FROM reservations WHERE kind='anthropic'").fetchone()[0]
            actual = db.execute("SELECT COALESCE(SUM(actual_microdollars),0) FROM settlements").fetchone()[0]
        return {"policy": self.policy, "requests_reserved": count, "liability_microdollars": liability,
                "settled_microdollars": actual, "pending_requests": pending,
                "dispatch_halted": bool(pending)}


def open_ledger(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise AdmissionError("Budget ledger is not initialized")
    with closing(sqlite3.connect(path.as_uri() + "?mode=rw", uri=True)) as db:
        row = db.execute("SELECT policy FROM pilot WHERE id=1").fetchone()
        if row is None:
            raise AdmissionError("Missing budget policy")
        policy = json.loads(row[0])
    return LiveBudgetLedger(path) if isinstance(policy, dict) and policy.get("mode") == "bounded_live" else BudgetLedger(path)
