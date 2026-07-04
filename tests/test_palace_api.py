from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app import main as app_main
from backend.app.auth import AuthenticatedUser
from backend.app.config import Settings


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        app_env="development",
        host="127.0.0.1",
        port=8001,
        app_base_url="http://127.0.0.1:8001",
        anthropic_api_key="",
        anthropic_api_url="https://api.anthropic.com/v1/messages",
        anthropic_max_tokens=8192,
        anthropic_timeout_seconds=180.0,
        cors_origins=("*",),
        trust_proxy_headers=False,
        rate_limit_requests=20,
        rate_limit_window_seconds=60,
        max_request_bytes=12000000,
        usage_log_path=tmp_path / "usage.jsonl",
        supabase_url="https://project.supabase.co",
        supabase_anon_key="anon-key",
        supabase_service_role_key="",
        supabase_jwt_audience="authenticated",
        free_monthly_requests=40,
        pro_monthly_requests=400,
        team_monthly_requests=4000,
        billing_mode="beta",
        gemini_api_key="",
        gemini_model="gemini-3-pro-image",
        gemini_text_model="gemini-3.1-pro-preview",
        gemini_image_model="gemini-3-pro-image",
        openai_api_key="",
        openai_embedding_model="text-embedding-3-small",
        openai_embedding_dimensions=1536,
        plan_override_path=tmp_path / "plan_overrides.json",
        admin_emails=(),
    )


class SupabaseMock:
    def __init__(self, responses: list[httpx.Response]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    async def __call__(self, **kwargs: Any) -> httpx.Response:
        self.calls.append(kwargs)
        if not self.responses:
            raise AssertionError("No mocked Supabase response left.")
        return self.responses.pop(0)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    settings = make_settings(tmp_path)

    async def fake_user(request: Any, active_settings: Settings) -> AuthenticatedUser:
        return AuthenticatedUser(
            user_id="user-123",
            email="patrick@example.com",
            claims={"sub": "user-123"},
        )

    monkeypatch.setattr(app_main, "_get_runtime_settings", lambda request: settings)
    monkeypatch.setattr(app_main, "_resolve_authenticated_user", fake_user)
    return TestClient(app_main.app)


def test_list_palaces_uses_backend_owned_supabase_query(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supabase = SupabaseMock([
        httpx.Response(
            200,
            json=[{
                "id": "palace-1",
                "title": "DKA Bar",
                "topic": "DKA",
                "scene_title": "The Drip Bar",
                "status": "generated",
                "latest_version_number": 1,
                "updated_at": "2026-06-29T12:00:00Z",
                "source_name": None,
            }],
        )
    ])
    monkeypatch.setattr(app_main, "_supabase_rest_request", supabase)

    response = client.get("/api/palaces", headers={"Authorization": "Bearer local-token"})

    assert response.status_code == 200
    assert response.json()["palaces"][0]["id"] == "palace-1"
    assert supabase.calls[0]["method"] == "GET"
    assert supabase.calls[0]["path"] == "/rest/v1/palaces"
    assert supabase.calls[0]["params"]["user_id"] == "eq.user-123"
    assert supabase.calls[0]["bearer_token"] == "local-token"


def test_ensure_profile_upserts_authenticated_user_through_backend(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supabase = SupabaseMock([
        httpx.Response(
            200,
            json=[{
                "id": "user-123",
                "email": "patrick@example.com",
                "display_name": "patrick",
            }],
        )
    ])
    monkeypatch.setattr(app_main, "_supabase_rest_request", supabase)

    response = client.post("/api/profile/ensure", headers={"Authorization": "Bearer local-token"})

    assert response.status_code == 200
    assert response.json()["profile"]["id"] == "user-123"
    assert supabase.calls[0]["method"] == "POST"
    assert supabase.calls[0]["path"] == "/rest/v1/profiles"
    assert supabase.calls[0]["params"] == {"on_conflict": "id"}
    assert supabase.calls[0]["headers"]["Prefer"] == "resolution=merge-duplicates,return=representation"
    assert supabase.calls[0]["json_body"] == {
        "id": "user-123",
        "email": "patrick@example.com",
        "display_name": "patrick",
    }
    assert supabase.calls[0]["bearer_token"] == "local-token"


def test_save_existing_palace_inserts_next_version_before_metadata_update(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supabase = SupabaseMock([
        httpx.Response(
            200,
            json=[{
                "id": "palace-1",
                "title": "Old title",
                "topic": "DKA",
                "scene_title": "Old scene",
                "status": "generated",
                "latest_version_number": 2,
                "updated_at": "2026-06-29T12:00:00Z",
                "source_name": None,
            }],
        ),
        httpx.Response(201, text=""),
        httpx.Response(
            200,
            json=[{
                "id": "palace-1",
                "title": "New title",
                "topic": "DKA management",
                "scene_title": "New scene",
                "status": "generated",
                "latest_version_number": 3,
                "updated_at": "2026-06-29T12:05:00Z",
                "source_name": "notes.txt",
            }],
        ),
    ])
    monkeypatch.setattr(app_main, "_supabase_rest_request", supabase)

    response = client.post(
        "/api/palaces/save",
        headers={"Authorization": "Bearer local-token"},
        json={
            "palace_id": "palace-1",
            "snapshot": {
                "title": "New title",
                "topic": "DKA management",
                "source_name": "notes.txt",
                "scene_title": "New scene",
                "status": "generated",
                "generation_inputs": {"topic": "DKA management"},
                "generation_outputs": {"story": {"scene_title": "New scene"}},
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["version_number"] == 3
    assert [call["method"] for call in supabase.calls] == ["GET", "POST", "PATCH"]
    assert supabase.calls[1]["path"] == "/rest/v1/palace_versions"
    assert supabase.calls[1]["json_body"]["version_number"] == 3
    assert supabase.calls[1]["json_body"]["generation_inputs"]["topic"] == "DKA management"
    assert supabase.calls[2]["json_body"]["latest_version_number"] == 3


def test_palace_routes_require_bearer_token(client: TestClient) -> None:
    response = client.get("/api/palaces")

    assert response.status_code == 401
    assert response.json()["detail"] == "Sign in to access saved palaces."


def test_profile_ensure_requires_bearer_token(client: TestClient) -> None:
    response = client.post("/api/profile/ensure")

    assert response.status_code == 401
    assert response.json()["detail"] == "Sign in to access saved palaces."


def test_catalog_publish_fails_closed_without_service_role_key(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = replace(make_settings(tmp_path), admin_emails=("patrick@example.com",))
    monkeypatch.setattr(app_main, "_get_runtime_settings", lambda request: settings)

    response = client.post(
        "/api/catalog/publish",
        headers={"Authorization": "Bearer local-token"},
        json={
            "title": "DKA Bar",
            "topic": "DKA",
            "tags": ["emergency"],
            "generation_inputs": {},
            "generation_outputs": {},
        },
    )

    assert response.status_code == 503
    assert "SUPABASE_SERVICE_ROLE_KEY" in response.json()["detail"]


def test_catalog_publish_uses_service_role_after_admin_check(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = replace(
        make_settings(tmp_path),
        supabase_service_role_key="service-role-key",
        admin_emails=("patrick@example.com",),
    )
    supabase = SupabaseMock([
        httpx.Response(
            201,
            json=[{
                "id": "11111111-1111-1111-1111-111111111111",
                "title": "DKA Bar",
                "topic": "DKA",
                "source_name": None,
                "scene_title": None,
                "tags": ["emergency"],
                "generation_inputs": {},
                "generation_outputs": {},
                "published_by": "user-123",
                "published_at": "2026-06-30T12:00:00Z",
            }],
        )
    ])

    monkeypatch.setattr(app_main, "_get_runtime_settings", lambda request: settings)
    monkeypatch.setattr(app_main, "_supabase_rest_request", supabase)

    response = client.post(
        "/api/catalog/publish",
        headers={"Authorization": "Bearer local-token"},
        json={
            "title": "DKA Bar",
            "topic": "DKA",
            "tags": ["Emergency", "emergency", " "],
            "generation_inputs": {},
            "generation_outputs": {},
        },
    )

    assert response.status_code == 200
    assert supabase.calls[0]["method"] == "POST"
    assert supabase.calls[0]["path"] == "/rest/v1/catalog_palaces"
    assert supabase.calls[0]["bearer_token"] is None
    assert supabase.calls[0]["use_service_role"] is True
    assert supabase.calls[0]["json_body"]["tags"] == ["emergency"]


def test_admin_diagnostics_requires_admin_email(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = replace(
        make_settings(tmp_path),
        supabase_service_role_key="service-role-key",
        admin_emails=("other@example.com",),
    )
    supabase = SupabaseMock([])
    monkeypatch.setattr(app_main, "_get_runtime_settings", lambda request: settings)
    monkeypatch.setattr(app_main, "_supabase_rest_request", supabase)

    response = client.get("/api/admin/diagnostics", headers={"Authorization": "Bearer local-token"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access is required."
    assert supabase.calls == []


def test_admin_diagnostics_requires_service_role_key(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = replace(make_settings(tmp_path), admin_emails=("patrick@example.com",))
    monkeypatch.setattr(app_main, "_get_runtime_settings", lambda request: settings)

    response = client.get("/api/admin/diagnostics", headers={"Authorization": "Bearer local-token"})

    assert response.status_code == 503
    assert "SUPABASE_SERVICE_ROLE_KEY" in response.json()["detail"]


def test_admin_diagnostics_uses_service_role_and_local_failure_log(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    usage_log = tmp_path / "usage.jsonl"
    usage_log.write_text(
        "\n".join([
            '{"timestamp":"2026-07-01T12:00:00+00:00","request_id":"ok-local","status_code":200,"model":"claude-test","input_tokens":10,"output_tokens":20}',
            '{"timestamp":"2026-07-01T12:01:00+00:00","request_id":"fail-local","status_code":529,"model":"claude-test","input_tokens":12,"output_tokens":0}',
        ]),
        encoding="utf-8",
    )
    settings = replace(
        make_settings(tmp_path),
        usage_log_path=usage_log,
        supabase_service_role_key="service-role-key",
        admin_emails=("patrick@example.com",),
    )
    supabase = SupabaseMock([
        httpx.Response(
            200,
            json=[{
                "id": "usage-1",
                "user_id": "user-123",
                "provider": "gemini",
                "model": "gemini-test",
                "request_id": "img-1",
                "input_tokens": None,
                "output_tokens": None,
                "status_code": 502,
                "created_at": "2026-07-01T12:02:00Z",
            }],
        ),
        httpx.Response(
            200,
            json=[{
                "id": "palace-1",
                "user_id": "user-123",
                "title": "DKA Bar",
                "topic": "DKA management " * 30,
                "scene_title": "The Drip Bar",
                "status": "generated",
                "latest_version_number": 2,
                "source_name": None,
                "updated_at": "2026-07-01T12:03:00Z",
            }],
        ),
        httpx.Response(
            200,
            json=[{
                "id": "catalog-1",
                "title": "DKA Bar",
                "topic": "DKA",
                "scene_title": "The Drip Bar",
                "tags": ["emergency"],
                "published_by": "user-123",
                "published_at": "2026-07-01T12:04:00Z",
            }],
        ),
    ])
    monkeypatch.setattr(app_main, "_get_runtime_settings", lambda request: settings)
    monkeypatch.setattr(app_main, "_supabase_rest_request", supabase)

    response = client.get("/api/admin/diagnostics", headers={"Authorization": "Bearer local-token"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["admin"]["email"] == "patrick@example.com"
    assert payload["summary"]["recent_usage_events"] == 1
    assert payload["summary"]["recent_usage_failures"] == 1
    assert payload["summary"]["recent_local_provider_failures"] == 1
    assert payload["recent_provider_failures"][0]["request_id"] in {"img-1", "fail-local"}
    assert payload["recent_palaces"][0]["topic_preview"].endswith("...")
    assert payload["catalog_publish_history"][0]["title"] == "DKA Bar"
    assert [call["path"] for call in supabase.calls] == [
        "/rest/v1/usage_events",
        "/rest/v1/palaces",
        "/rest/v1/catalog_palaces",
    ]
    assert all(call["use_service_role"] is True for call in supabase.calls)
    assert all(call["bearer_token"] is None for call in supabase.calls)


def test_admin_catalog_seed_list_uses_service_role(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = replace(
        make_settings(tmp_path),
        supabase_service_role_key="service-role-key",
        admin_emails=("patrick@example.com",),
    )
    supabase = SupabaseMock([
        httpx.Response(200, json=[]),
    ])
    monkeypatch.setattr(app_main, "_get_runtime_settings", lambda request: settings)
    monkeypatch.setattr(app_main, "_supabase_rest_request", supabase)

    response = client.get("/api/admin/catalog-seeds", headers={"Authorization": "Bearer local-token"})

    assert response.status_code == 200
    assert response.json()["seeds"][0]["slug"] == "dka-management"
    assert response.json()["seeds"][0]["published"] is False
    assert supabase.calls[0]["path"] == "/rest/v1/catalog_palaces"
    assert supabase.calls[0]["use_service_role"] is True
    assert supabase.calls[0]["bearer_token"] is None
    assert supabase.calls[0]["params"]["tags"] == "cs.{seed:dka-management}"


def test_admin_catalog_seed_publish_inserts_seed_once(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = replace(
        make_settings(tmp_path),
        supabase_service_role_key="service-role-key",
        admin_emails=("patrick@example.com",),
    )
    supabase = SupabaseMock([
        httpx.Response(200, json=[]),
        httpx.Response(
            201,
            json=[{
                "id": "catalog-1",
                "title": "DKA Management: The Midnight Drip Bar",
                "topic": "DKA",
                "scene_title": "The Midnight Drip Bar",
                "tags": ["dka", "seed:dka-management", "seed-version:1"],
                "published_by": "user-123",
                "published_at": "2026-07-01T12:00:00Z",
                "generation_inputs": {
                    "seed": {"source": "catalog_seed", "slug": "dka-management", "version": 1}
                },
            }],
        ),
    ])
    monkeypatch.setattr(app_main, "_get_runtime_settings", lambda request: settings)
    monkeypatch.setattr(app_main, "_supabase_rest_request", supabase)

    response = client.post(
        "/api/admin/catalog-seeds/publish",
        headers={"Authorization": "Bearer local-token"},
        json={"slug": "dka-management"},
    )

    assert response.status_code == 200
    assert response.json()["published"] is True
    assert response.json()["updated"] is False
    assert [call["method"] for call in supabase.calls] == ["GET", "POST"]
    insert_body = supabase.calls[1]["json_body"]
    assert insert_body["published_by"] == "user-123"
    assert "seed:dka-management" in insert_body["tags"]
    assert "seed-version:1" in insert_body["tags"]
    assert insert_body["generation_inputs"]["seed"] == {
        "source": "catalog_seed",
        "slug": "dka-management",
        "version": 1,
    }
    assert supabase.calls[1]["use_service_role"] is True
    assert supabase.calls[1]["bearer_token"] is None


def test_admin_catalog_seed_publish_is_idempotent_for_current_version(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = replace(
        make_settings(tmp_path),
        supabase_service_role_key="service-role-key",
        admin_emails=("patrick@example.com",),
    )
    existing = {
        "id": "catalog-1",
        "title": "DKA Management: The Midnight Drip Bar",
        "topic": "DKA",
        "scene_title": "The Midnight Drip Bar",
        "tags": ["dka", "seed:dka-management", "seed-version:1"],
        "published_by": "user-123",
        "published_at": "2026-07-01T12:00:00Z",
        "generation_inputs": {
            "seed": {"source": "catalog_seed", "slug": "dka-management", "version": 1}
        },
    }
    supabase = SupabaseMock([httpx.Response(200, json=[existing])])
    monkeypatch.setattr(app_main, "_get_runtime_settings", lambda request: settings)
    monkeypatch.setattr(app_main, "_supabase_rest_request", supabase)

    response = client.post(
        "/api/admin/catalog-seeds/publish",
        headers={"Authorization": "Bearer local-token"},
        json={"slug": "dka-management"},
    )

    assert response.status_code == 200
    assert response.json()["published"] is False
    assert response.json()["updated"] is False
    assert response.json()["entry"]["id"] == "catalog-1"
    assert [call["method"] for call in supabase.calls] == ["GET"]


def test_admin_catalog_seed_publish_updates_existing_old_version(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = replace(
        make_settings(tmp_path),
        supabase_service_role_key="service-role-key",
        admin_emails=("patrick@example.com",),
    )
    existing = {
        "id": "catalog-1",
        "title": "Old DKA",
        "topic": "Old topic",
        "scene_title": "Old",
        "tags": ["seed:dka-management", "seed-version:0"],
        "published_by": "user-123",
        "published_at": "2026-07-01T12:00:00Z",
        "generation_inputs": {
            "seed": {"source": "catalog_seed", "slug": "dka-management", "version": 0}
        },
    }
    updated = {
        **existing,
        "title": "DKA Management: The Midnight Drip Bar",
        "tags": ["dka", "seed:dka-management", "seed-version:1"],
        "generation_inputs": {
            "seed": {"source": "catalog_seed", "slug": "dka-management", "version": 1}
        },
    }
    supabase = SupabaseMock([
        httpx.Response(200, json=[existing]),
        httpx.Response(200, json=[updated]),
    ])
    monkeypatch.setattr(app_main, "_get_runtime_settings", lambda request: settings)
    monkeypatch.setattr(app_main, "_supabase_rest_request", supabase)

    response = client.post(
        "/api/admin/catalog-seeds/publish",
        headers={"Authorization": "Bearer local-token"},
        json={"slug": "dka-management"},
    )

    assert response.status_code == 200
    assert response.json()["published"] is True
    assert response.json()["updated"] is True
    assert [call["method"] for call in supabase.calls] == ["GET", "PATCH"]
    assert supabase.calls[1]["params"] == {"id": "eq.catalog-1"}
    assert supabase.calls[1]["json_body"]["published_by"] == "user-123"


def test_medical_context_uses_service_role_and_returns_capped_excerpts(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = replace(
        make_settings(tmp_path),
        supabase_service_role_key="service-role-key",
        openai_api_key="openai-key",
    )
    long_chunk = "DKA management requires careful fluids and potassium checks. " * 20
    supabase = SupabaseMock([
        httpx.Response(
            200,
            json=[{
                "chunk_id": "chunk-1",
                "source_key": "tintin-endocrine",
                "title": "Tintin Endocrine",
                "page_start": 12,
                "page_end": 13,
                "section_title": "DKA",
                "chunk_text": long_chunk,
                "similarity": 0.82,
                "keyword_rank": 0.4,
            }],
        )
    ])
    scheduled_usage: list[dict[str, Any]] = []

    async def fake_summary(**kwargs: Any) -> dict[str, Any]:
        return {
            "plan_code": "free",
            "subscription_status": "inactive",
            "monthly_request_limit": 40,
            "monthly_requests_used": 0,
            "monthly_requests_remaining": 40,
            "period_started_at": "2026-06-01T00:00:00+00:00",
            "period_ends_at": "2026-07-01T00:00:00+00:00",
            "is_dev_override": False,
        }

    async def fake_embedding(**kwargs: Any) -> tuple[list[float], dict[str, Any]]:
        return [0.01] * 1536, {"prompt_tokens": 8}

    def fake_schedule_usage_event(**kwargs: Any) -> None:
        scheduled_usage.append(kwargs)

    monkeypatch.setattr(app_main, "_get_runtime_settings", lambda request: settings)
    monkeypatch.setattr(app_main, "_get_subscription_and_usage_summary", fake_summary)
    monkeypatch.setattr(app_main, "_create_openai_embedding", fake_embedding)
    monkeypatch.setattr(app_main, "_supabase_rest_request", supabase)
    monkeypatch.setattr(app_main, "_schedule_usage_event", fake_schedule_usage_event)

    response = client.post(
        "/api/medical-knowledge/context",
        headers={"Authorization": "Bearer local-token"},
        json={"topic": "DKA fluids and potassium", "max_chunks": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert "chunk_text" not in response.text
    assert payload["context"][0]["excerpt"].endswith("...")
    assert len(payload["context"][0]["excerpt"]) <= 420
    assert supabase.calls[0]["path"] == "/rest/v1/rpc/match_medical_knowledge_chunks"
    assert supabase.calls[0]["bearer_token"] is None
    assert supabase.calls[0]["use_service_role"] is True
    assert supabase.calls[0]["json_body"]["p_match_count"] == 3
    assert scheduled_usage[0]["request_body"]["provider"] == "openai"


def test_medical_quality_check_reports_missing_required_concepts_without_raw_chunks(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = replace(
        make_settings(tmp_path),
        supabase_service_role_key="service-role-key",
        openai_api_key="openai-key",
    )

    async def fake_summary(**kwargs: Any) -> dict[str, Any]:
        return {
            "plan_code": "free",
            "subscription_status": "inactive",
            "monthly_request_limit": 40,
            "monthly_requests_used": 0,
            "monthly_requests_remaining": 40,
            "period_started_at": "2026-06-01T00:00:00+00:00",
            "period_ends_at": "2026-07-01T00:00:00+00:00",
            "is_dev_override": False,
        }

    async def fake_retrieve(**kwargs: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        return [
            {
                "source_key": "tintin-endocrine",
                "title": "Tintin Endocrine",
                "page_start": 12,
                "page_end": 12,
                "section_title": "DKA",
                "chunk_text": "potassium must be checked before insulin",
                "similarity": 0.9,
                "keyword_rank": 0.5,
            }
        ], {"prompt_tokens": 6}

    monkeypatch.setattr(app_main, "_get_runtime_settings", lambda request: settings)
    monkeypatch.setattr(app_main, "_get_subscription_and_usage_summary", fake_summary)
    monkeypatch.setattr(app_main, "_retrieve_medical_context", fake_retrieve)
    monkeypatch.setattr(app_main, "_schedule_usage_event", lambda **kwargs: None)

    response = client.post(
        "/api/medical-knowledge/quality-check",
        headers={"Authorization": "Bearer local-token"},
        json={
            "topic": "DKA",
            "generation_outputs": {"script": "Give fluids first."},
            "required_concepts": ["potassium"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["verdict"] == "needs_repair"
    assert payload["repair_focus"] == ["potassium"]
    assert payload["required_concept_coverage"][0]["evidence_refs"][0]["source_key"] == "tintin-endocrine"
    assert "potassium must be checked before insulin" not in response.text


def test_medical_quality_check_suppresses_cross_topic_citations(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = replace(
        make_settings(tmp_path),
        supabase_service_role_key="service-role-key",
        openai_api_key="openai-key",
    )

    async def fake_summary(**kwargs: Any) -> dict[str, Any]:
        return {
            "plan_code": "free",
            "subscription_status": "inactive",
            "monthly_request_limit": 40,
            "monthly_requests_used": 0,
            "monthly_requests_remaining": 40,
            "period_started_at": "2026-06-01T00:00:00+00:00",
            "period_ends_at": "2026-07-01T00:00:00+00:00",
            "is_dev_override": False,
        }

    async def fake_retrieve(**kwargs: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        return [
            {
                "source_key": "tintin-endocrine",
                "title": "Tintin Endocrine",
                "page_start": 38,
                "page_end": 38,
                "section_title": "DKA",
                "chunk_text": "shock and fluids in endocrine emergencies",
                "similarity": 0.53,
                "keyword_rank": 0.46,
            }
        ], {"prompt_tokens": 6}

    monkeypatch.setattr(app_main, "_get_runtime_settings", lambda request: settings)
    monkeypatch.setattr(app_main, "_get_subscription_and_usage_summary", fake_summary)
    monkeypatch.setattr(app_main, "_retrieve_medical_context", fake_retrieve)
    monkeypatch.setattr(app_main, "_schedule_usage_event", lambda **kwargs: None)

    response = client.post(
        "/api/medical-knowledge/quality-check",
        headers={"Authorization": "Bearer local-token"},
        json={
            "topic": "ATLS trauma primary survey",
            "generation_outputs": {"script": "Airway comes first in ATLS."},
            "required_concepts": ["airway"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["evidence_status"] == "no_relevant_source"
    assert payload["evidence_count"] == 0
    assert payload["evidence"] == []
    assert payload["required_concept_coverage"][0]["evidence_refs"] == []
    assert "Tintin Endocrine" not in response.text
