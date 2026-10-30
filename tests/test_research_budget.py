"""Offline spend-admission rehearsal; these tests never call a real provider."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import asyncio
import json
import sqlite3
import subprocess
import sys

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app import main
from backend.app.research_budget import (
    AdmissionError, BudgetLedger, LiveBudgetLedger, COUNT_URL, MODEL, MODEL_URL, MODEL_INPUT_BOUND,
    LIVE_RESERVATION, EMBEDDING_RESERVATION, RESERVATION, STAGES, open_ledger, validate_request,
)


def policy(**changes):
    return {"version": 1, "mode": "dry_run", "pilot_id": "rehearsal", "topic_ids": ["one", "two", "three"],
            "cap_microdollars": 6000000, "max_calls": 24, **changes}


def body(**changes):
    return {"model": MODEL, "max_tokens": 6144, "system": "Nonclinical fixture instructions.",
            "messages": [{"role": "user", "content": "Workshop objects"}], **changes}


def test_scene_tool_preserves_final_count_payload():
    request = body(tools=[{"name":"submit_memory_palace", "description":"Bounded scene.",
        "strict":True, "input_schema":{"type":"object","properties":{},"additionalProperties":False}}],
        tool_choice={"type":"tool","name":"submit_memory_palace","disable_parallel_tool_use":True})
    counted = validate_request(request, {})
    assert counted["tools"] == request["tools"]
    assert counted["tool_choice"] == request["tool_choice"]
    request["tool_choice"]["name"] = "submit_visual_preflight_review"
    with pytest.raises(AdmissionError, match="tool choice"):
        validate_request(request, {})


def test_restart_caps_all_arms_and_no_reset(tmp_path):
    path = tmp_path / "budget.sqlite3"
    ledger = BudgetLedger.create(path, policy())
    for topic in ("one", "two", "three"):
        for arm in ("baseline", "candidate"):
            for stage in STAGES:
                receipt = ledger.reserve(f"{topic}-{arm}-{stage}", topic, arm, stage, body(), 30000, {})
                assert receipt["live_authorized"] is False
    assert BudgetLedger(path).report()["reserved_microdollars"] == RESERVATION * 24 == 4371840
    with pytest.raises(AdmissionError, match="ceiling exhausted"):
        ledger.reserve("extra", "one", "baseline", STAGES[0], body(), 3, {})
    with pytest.raises(FileExistsError):
        BudgetLedger.create(path, policy())


def test_concurrent_reservations_are_atomic(tmp_path):
    path = tmp_path / "budget.sqlite3"
    BudgetLedger.create(path, policy(max_calls=1))
    def reserve(i):
        try:
            return BudgetLedger(path).reserve(str(i), "one", "baseline", STAGES[0], body(), 10, {})
        except AdmissionError:
            return None
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(result is not None for result in pool.map(reserve, range(16))) == 1
    assert BudgetLedger(path).report()["requests_reserved"] == 1


def test_money_ceiling_timeout_reservation_never_released(tmp_path):
    ledger = BudgetLedger.create(tmp_path / "budget.sqlite3", policy(cap_microdollars=RESERVATION))
    ledger.reserve("uncertain", "one", "baseline", STAGES[0], body(), 1, {})
    with pytest.raises(AdmissionError, match="ceiling"):
        ledger.reserve("later", "two", "baseline", STAGES[0], body(), 1, {})
    assert ledger.report()["reserved_microdollars"] == RESERVATION


@pytest.mark.parametrize("changes", [{"mode": "live"}, {"cap_microdollars": 6000001}, {"max_calls": 25},
    {"topic_ids": ["one", "one"]}, {"version": 2}])
def test_no_live_mode_or_expanded_budget(tmp_path, changes):
    with pytest.raises(AdmissionError):
        BudgetLedger.create(tmp_path / "no.sqlite3", policy(**changes))


@pytest.mark.parametrize("changes", [{"model": "unknown"}, {"max_tokens": 6145}, {"betas": ["advisor"]},
    {"cache_control": {}}, {"tools": [{"type": "web_search", "name": "web_search"}]},
    {"messages": [{"role": "user", "content": [{"type": "image"}]}]}])
def test_unknown_billing_features_rejected(changes):
    with pytest.raises(AdmissionError):
        validate_request(body(**changes), {})


def test_final_tools_are_counted_and_input_not_mutated():
    request = body(tools=[{"name": "submit_visual_preflight_review", "description": "Review.", "strict": True,
                          "input_schema": {"type": "object", "properties": {}}}],
                   tool_choice={"type": "tool", "name": "submit_visual_preflight_review", "disable_parallel_tool_use": True})
    before = json.dumps(request)
    counted = validate_request(request, {})
    assert counted["tools"] == request["tools"] and counted["system"] == request["system"]
    assert "max_tokens" not in counted and json.dumps(request) == before


def test_stage_model_input_and_policy_fail_closed(tmp_path):
    ledger = BudgetLedger.create(tmp_path / "budget.sqlite3", policy())
    with pytest.raises(AdmissionError, match="Stage"):
        ledger.reserve("bad-stage", "one", "baseline", STAGES[1], body(), 10, {})
    for count in (None, True, -1, 30001):
        with pytest.raises(AdmissionError):
            ledger.reserve("bad-count", "one", "baseline", STAGES[0], body(), count, {})
    assert ledger.report()["requests_reserved"] == 0
    with sqlite3.connect(ledger.path) as db:
        db.execute("UPDATE pilot SET policy=?", (json.dumps(policy(max_calls=2)),))
    with pytest.raises(AdmissionError, match="changed"):
        ledger.reserve("changed", "one", "baseline", STAGES[0], body(), 1, {})


def configure_server(monkeypatch, tmp_path, configured=True):
    monkeypatch.setattr(main, "REPO_ROOT", tmp_path)
    path = tmp_path / "Troubleshooting Prompts" / "rehearsal.sqlite3"
    if configured:
        BudgetLedger.create(path, policy())
    settings = replace(main.get_settings(), anthropic_api_key="test-key", app_env="development", demo_auth_bypass=True,
                       supabase_url="", supabase_anon_key="", supabase_service_role_key="", openai_api_key="",
                       usage_log_path=tmp_path / "usage.jsonl",
                       research_budget_path=path if configured else None)
    monkeypatch.setitem(main.app.state._state, "settings", settings)
    return path


HEADERS = {"x-forge-first-attempt": "v1", "x-research-topic-id": "one", "x-research-arm": "baseline",
           "x-research-stage": STAGES[0]}


def test_profile_cannot_call_unconfigured_server(monkeypatch, tmp_path):
    configure_server(monkeypatch, tmp_path, False)
    response = TestClient(main.app).post("/api/anthropic/messages", json=body(), headers=HEADERS)
    assert response.status_code == 409 and response.json()["error"]["type"] == "research_not_configured"


@pytest.mark.parametrize("outcome", ["success", "timeout", "invalid", "limit", "error"])
def test_guard_counts_final_body_and_never_dispatches_generation(monkeypatch, tmp_path, outcome):
    path = configure_server(monkeypatch, tmp_path)
    calls = []
    class Counter:
        async def post(self, url, **kwargs):
            calls.append((url, kwargs["json"]))
            assert url == COUNT_URL  # Any billable message dispatch fails this test.
            if outcome == "timeout":
                raise httpx.ReadTimeout("fixture timeout")
            if outcome == "error":
                return httpx.Response(500)
            return httpx.Response(200, json={"input_tokens": 30001 if outcome == "limit" else 25} if outcome != "invalid" else [])
    monkeypatch.setattr(main, "_get_http_client", lambda request: (Counter(), False))
    # Actual evidence injection executes; only retrieval itself is a nonclinical stub.
    settings = replace(main.app.state.settings, supabase_url="https://fixture.supabase.co", supabase_anon_key="fixture",
                       supabase_service_role_key="fixture", openai_api_key="fixture")
    monkeypatch.setitem(main.app.state._state, "settings", settings)
    async def retrieve(**kwargs):
        return [{"title": "Workshop", "source_key": "fixture", "page_start": 1, "page_end": 1,
                 "similarity": .9, "chunk_text": "Workshop fixture evidence."}], {}
    monkeypatch.setattr(main, "_retrieve_medical_context", retrieve)
    monkeypatch.setattr(main, "_topic_relevant_medical_rows", lambda rows, *args, **kwargs: rows)
    headers = {**HEADERS, "x-evidence-grounding": "true", "x-evidence-topic": "Workshop"}
    response = TestClient(main.app).post("/api/anthropic/messages", json=body(), headers=headers)
    assert response.status_code == 409 and len(calls) == 1
    assert "Workshop fixture evidence." in calls[0][1]["system"]
    assert "max_tokens" not in calls[0][1]
    if outcome == "success":
        receipt = response.json()["research_admission"]
        assert not receipt["live_authorized"] and not receipt["financial_guarantee"]
        assert BudgetLedger(path).report()["requests_reserved"] == 1
    else:
        assert BudgetLedger(path).report()["requests_reserved"] == 0


def test_other_provider_lanes_disabled_in_rehearsal(monkeypatch, tmp_path):
    configure_server(monkeypatch, tmp_path)
    client = TestClient(main.app)
    for route in ("/api/generate-image", "/api/gemini/prompt-director", "/api/elevenlabs/tts"):
        assert client.post(route, json={}).status_code == 409
    assert client.get("/api/diagnose-gemini").status_code == 409


def test_live_embeddings_block_before_transport(monkeypatch, tmp_path):
    configure_server(monkeypatch, tmp_path)
    def forbidden(request):
        pytest.fail("No outbound embedding transport may be acquired")
    monkeypatch.setattr(main, "_get_http_client", forbidden)
    with pytest.raises(main.HTTPException) as caught:
        asyncio.run(main._create_openai_embedding(request=None, settings=main.app.state.settings, text="Fixture"))
    assert caught.value.status_code == 409


@pytest.mark.parametrize("kind", ["replay", "exhausted", "missing-header", "bad-policy", "bad-model", "beta"])
def test_pre_admission_blocks_before_any_outbound_request(monkeypatch, tmp_path, kind):
    path = configure_server(monkeypatch, tmp_path)
    headers = dict(HEADERS)
    request = body()
    if kind == "replay":
        headers["x-forge-replay"] = "replay"
        monkeypatch.setattr(main, "load_cassette", lambda *args: pytest.fail("Replay branch must not be reached"))
    elif kind == "exhausted":
        BudgetLedger(path).reserve("old", "one", "baseline", STAGES[0], body(), 10, {})
    elif kind == "missing-header":
        headers = {}
    elif kind == "bad-policy":
        with sqlite3.connect(path) as db:
            db.execute("UPDATE pilot SET policy='null'")
    elif kind == "bad-model":
        request["model"] = "unknown-model"
    else:
        headers["Anthropic-Beta"] = "advisor"
    monkeypatch.setattr(main, "_get_http_client", lambda request: pytest.fail("Rejected before outbound transport"))
    response = TestClient(main.app).post("/api/anthropic/messages", json=request, headers=headers)
    assert response.status_code == 409


@pytest.mark.parametrize("stored", ["null", "[]", '{"pilot_id":4}', "{}"])
def test_malformed_stored_policy_controlled_rejection(monkeypatch, tmp_path, stored):
    path = configure_server(monkeypatch, tmp_path)
    with sqlite3.connect(path) as db:
        db.execute("UPDATE pilot SET policy=?", (stored,))
    response = TestClient(main.app).post("/api/anthropic/messages", json=body(), headers=HEADERS)
    assert response.status_code == 409


def test_reservations_cannot_be_deleted_or_released(tmp_path):
    ledger = BudgetLedger.create(tmp_path / "budget.sqlite3", policy())
    ledger.reserve("one", "one", "baseline", STAGES[0], body(), 10, {})
    for statement in ("DELETE FROM reservations", "UPDATE reservations SET reserved_microdollars=0"):
        with sqlite3.connect(ledger.path) as db, pytest.raises(sqlite3.IntegrityError):
            db.execute(statement)
    assert ledger.report()["requests_reserved"] == 1


def live_policy(**changes):
    return policy(version=2, mode="bounded_live", **changes)


def live_body(**changes):
    return body(service_tier="standard_only", inference_geo="global", **changes)


def live_response(name="msg_fixture", input_tokens=10, output_tokens=20, **changes):
    return {"id": name, "model": MODEL, "stop_reason": "end_turn", "content": [{"type": "text", "text": "Fixture response."}],
            "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens,
                      "service_tier": "standard", "inference_geo": "global", "speed": "standard"}, **changes}


def test_full_bound_reservation_then_verified_settlement(tmp_path):
    path = tmp_path / "budget.sqlite3"
    ledger = LiveBudgetLedger.create(path, live_policy())
    assert isinstance(open_ledger(path), LiveBudgetLedger)
    receipt = ledger.reserve("r1", "one", "baseline", STAGES[0], live_body(), 20, {})
    assert receipt["reserved_microdollars"] == LIVE_RESERVATION == 3092160
    with pytest.raises(AdmissionError, match="Pending"):
        LiveBudgetLedger(path).reserve("r2", "two", "baseline", STAGES[0], live_body(), 20, {})
    ledger.settle("r1", live_body(), live_response())
    assert ledger.report()["liability_microdollars"] == 330
    assert not ledger.report()["dispatch_halted"]
    ledger.reserve("r2", "one", "baseline", STAGES[1], live_body(), 20, {})
    assert LiveBudgetLedger(path).report()["pending_requests"] == 1
    with pytest.raises(AdmissionError):
        ledger.settle("r2", live_body(), live_response())  # Same provider response cannot fund two requests.
    assert ledger.report()["pending_requests"] == 1


@pytest.mark.parametrize("prior,allowed", [(2907840, True), (2907841, False)])
def test_live_exact_cap_boundary(tmp_path, prior, allowed):
    ledger = LiveBudgetLedger.create(tmp_path / "budget.sqlite3", live_policy())
    ledger.reserve("first", "one", "baseline", STAGES[0], live_body(), 10, {})
    # Every integer liability can be represented with the pinned $3 input rate
    # only in multiples of 3; seed one conservative embedding-cent remainder.
    with sqlite3.connect(ledger.path) as db:
        db.execute("INSERT INTO settlements VALUES(?,?,?,?,?)", ("first", prior, "fixture", "{}", "msg_seed"))
    if allowed:
        receipt = ledger.reserve("next", "two", "baseline", STAGES[0], live_body(), 10, {})
        assert receipt["total_liability_microdollars"] == 6000000
    else:
        with pytest.raises(AdmissionError, match="remaining cap"):
            ledger.reserve("next", "two", "baseline", STAGES[0], live_body(), 10, {})


def test_live_concurrent_single_inflight(tmp_path):
    path = tmp_path / "budget.sqlite3"
    LiveBudgetLedger.create(path, live_policy())
    def reserve(i):
        try:
            return LiveBudgetLedger(path).reserve(str(i), "one", "baseline", STAGES[0], live_body(), 20, {})
        except AdmissionError:
            return None
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(r is not None for r in pool.map(reserve, range(12))) == 1
    assert LiveBudgetLedger(path).report()["pending_requests"] == 1


def test_live_reservation_is_process_safe_and_survives_process_exit(tmp_path):
    path = tmp_path / "budget.sqlite3"
    LiveBudgetLedger.create(path, live_policy())
    code = """
import sys
from pathlib import Path
from backend.app.research_budget import LiveBudgetLedger,AdmissionError,MODEL,STAGES
body={'model':MODEL,'max_tokens':6144,'system':'Fixture','service_tier':'standard_only','inference_geo':'global','messages':[{'role':'user','content':'Workshop'}]}
try:
 LiveBudgetLedger(Path(sys.argv[1])).reserve(sys.argv[2],'one','baseline',STAGES[0],body,10,{})
 print('admitted')
except AdmissionError:
 print('blocked')
"""
    def reserve(i):
        return subprocess.run([sys.executable, "-c", code, str(path), str(i)], capture_output=True,
                              text=True, check=True, timeout=20).stdout.strip()
    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes = list(pool.map(reserve, range(4)))
    assert outcomes.count("admitted") == 1 and outcomes.count("blocked") == 3
    assert LiveBudgetLedger(path).report()["pending_requests"] == 1


@pytest.mark.parametrize("mutation", ["missing", "negative", "bool", "input_over", "output_over", "model", "premium", "unknown", "nested_unknown", "nested_type"])
def test_invalid_settlement_never_releases_bound(tmp_path, mutation):
    ledger = LiveBudgetLedger.create(tmp_path / "budget.sqlite3", live_policy())
    ledger.reserve("pending", "one", "baseline", STAGES[0], live_body(), 10, {})
    result = live_response()
    if mutation == "missing": result.pop("usage")
    elif mutation == "model": result["model"] = "other"
    elif mutation == "premium": result["usage"]["service_tier"] = "priority"
    elif mutation == "unknown": result["usage"]["new_billable_feature"] = 1
    elif mutation == "nested_unknown": result["usage"]["output_tokens_details"] = {"unknown": 0}
    elif mutation == "nested_type": result["usage"]["output_tokens_details"] = []
    else: result["usage"]["input_tokens" if mutation != "output_over" else "output_tokens"] = {
        "negative": -1, "bool": True, "input_over": 1000001, "output_over": 6145}[mutation]
    with pytest.raises(AdmissionError): ledger.settle("pending", live_body(), result)
    assert ledger.report()["liability_microdollars"] == LIVE_RESERVATION
    assert LiveBudgetLedger(ledger.path).report()["dispatch_halted"]


def test_embedding_is_in_same_total_bound(tmp_path):
    ledger = LiveBudgetLedger.create(tmp_path / "budget.sqlite3", live_policy())
    request = {"model": "text-embedding-3-small", "input": "Workshop"}
    ledger.reserve_embedding("embed", request)
    with pytest.raises(AdmissionError):
        ledger.reserve("scene", "one", "baseline", STAGES[0], live_body(), 10, {})
    ledger.settle_embedding("embed", request, {"model": "text-embedding-3-small", "usage": {"prompt_tokens": 2, "total_tokens": 2}})
    assert ledger.report()["liability_microdollars"] == EMBEDDING_RESERVATION == 164
    ledger.reserve("scene", "one", "baseline", STAGES[0], live_body(), 10, {})
    assert ledger.report()["liability_microdollars"] == LIVE_RESERVATION + 164


@pytest.mark.parametrize("value", [["one", "two"], [1, 2, 3], "", None])
def test_live_embedding_cannot_expand_into_multiple_inputs(tmp_path, value):
    ledger = LiveBudgetLedger.create(tmp_path / "budget.sqlite3", live_policy())
    with pytest.raises(AdmissionError):
        ledger.reserve_embedding("bad", {"model": "text-embedding-3-small", "input": value})
    assert ledger.report()["liability_microdollars"] == 0


@pytest.mark.parametrize("mode", ["success", "timeout", "bad_usage", "bad_metadata", "nonjson", "non200"])
def test_live_backend_dispatch_and_uncertainty_lock(monkeypatch, tmp_path, mode):
    path = configure_server(monkeypatch, tmp_path, configured=False)
    ledger = LiveBudgetLedger.create(path, live_policy())
    monkeypatch.setitem(main.app.state._state, "settings", replace(main.app.state.settings, research_budget_path=path))
    calls = []
    class Provider:
        async def get(self, url, **kwargs):
            assert url == MODEL_URL
            return httpx.Response(200, json={"id": MODEL, "max_input_tokens": 2000000 if mode == "bad_metadata" else MODEL_INPUT_BOUND, "max_tokens": 128000})
        async def post(self, url, **kwargs):
            calls.append(url)
            if url == COUNT_URL:
                return httpx.Response(200, json={"input_tokens": 20})
            assert url == main.MESSAGE_URL and ledger.report()["pending_requests"] == 1
            assert kwargs["follow_redirects"] is False
            if mode == "timeout": raise httpx.ReadTimeout("fixture timeout")
            if mode == "nonjson": return httpx.Response(200, text="not json")
            result = live_response()
            if mode == "bad_usage": result.pop("usage")
            return httpx.Response(201 if mode == "non200" else 200, json=result)
    monkeypatch.setattr(main, "_get_http_client", lambda request: (Provider(), False))
    response = TestClient(main.app).post("/api/anthropic/messages", json=body(), headers=HEADERS)
    if mode == "success":
        assert response.status_code == 200 and ledger.report()["liability_microdollars"] == 330
        assert list((path.parent / "provider_packets").glob("*.request.json"))
    elif mode == "bad_metadata":
        assert response.status_code == 409 and calls == [] and ledger.report()["requests_reserved"] == 0
    else:
        assert response.status_code in (502, 504) and ledger.report()["liability_microdollars"] == LIVE_RESERVATION
        before = len(calls)
        assert TestClient(main.app).post("/api/anthropic/messages", json=body(), headers=HEADERS).status_code == 409
        assert len(calls) == before


@pytest.mark.parametrize("status", [200, 201, 302])
def test_live_embedding_transport_requires_exact_success(monkeypatch, tmp_path, status):
    path = configure_server(monkeypatch, tmp_path, configured=False)
    ledger = LiveBudgetLedger.create(path, live_policy())
    settings = replace(main.app.state.settings, research_budget_path=path, openai_api_key="test-key")
    class Provider:
        async def post(self, url, **kwargs):
            assert url == main.OPENAI_EMBEDDINGS_URL and kwargs["follow_redirects"] is False
            assert ledger.report()["pending_requests"] == 1
            return httpx.Response(status, json={"model": "text-embedding-3-small", "data": [{"embedding": [.1]}],
                                               "usage": {"prompt_tokens": 2, "total_tokens": 2}})
    monkeypatch.setattr(main, "_get_http_client", lambda request: (Provider(), False))
    if status == 200:
        asyncio.run(main._create_openai_embedding(request=None, settings=settings, text="Workshop"))
        assert ledger.report()["pending_requests"] == 0 and ledger.report()["settled_microdollars"] == 164
    else:
        with pytest.raises(main.HTTPException) as error:
            asyncio.run(main._create_openai_embedding(request=None, settings=settings, text="Workshop"))
        assert error.value.status_code == 502 and ledger.report()["pending_requests"] == 1
