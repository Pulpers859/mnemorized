from __future__ import annotations

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
        supabase_jwt_audience="authenticated",
        free_monthly_requests=40,
        pro_monthly_requests=400,
        team_monthly_requests=4000,
        gemini_api_key="",
        gemini_model="gemini-2.5-flash-image",
        plan_override_path=tmp_path / "plan_overrides.json",
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
