from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app import main as app_main
from backend.app.auth import AuthenticatedUser
from backend.app.config import Settings


def make_settings(
    tmp_path: Path,
    *,
    app_env: str = "development",
    anthropic_api_key: str = "",
    gemini_api_key: str = "",
    supabase_url: str = "",
    supabase_anon_key: str = "",
) -> Settings:
    return Settings(
        app_env=app_env,
        host="127.0.0.1",
        port=8001,
        app_base_url="http://127.0.0.1:8001",
        anthropic_api_key=anthropic_api_key,
        anthropic_api_url="https://api.anthropic.com/v1/messages",
        anthropic_max_tokens=8192,
        anthropic_timeout_seconds=180.0,
        cors_origins=("*",),
        trust_proxy_headers=False,
        rate_limit_requests=20,
        rate_limit_window_seconds=60,
        max_request_bytes=12000000,
        usage_log_path=tmp_path / "usage.jsonl",
        supabase_url=supabase_url,
        supabase_anon_key=supabase_anon_key,
        supabase_jwt_audience="authenticated",
        free_monthly_requests=40,
        pro_monthly_requests=400,
        team_monthly_requests=4000,
        gemini_api_key=gemini_api_key,
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


class FakeProviderClient:
    def __init__(self, responses: list[httpx.Response]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    async def post(self, *args: Any, **kwargs: Any) -> httpx.Response:
        self.calls.append({"args": args, **kwargs})
        if not self.responses:
            raise AssertionError("No mocked provider response left.")
        return self.responses.pop(0)


def test_cors_allows_library_mutation_methods() -> None:
    client = TestClient(app_main.app)

    response = client.options(
        "/api/palaces/palace-1",
        headers={
            "Origin": "http://localhost:9000",
            "Access-Control-Request-Method": "DELETE",
        },
    )

    assert response.status_code == 200
    allow_methods = response.headers["access-control-allow-methods"]
    assert "PATCH" in allow_methods
    assert "DELETE" in allow_methods


def test_production_provider_auth_fails_closed_when_supabase_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, app_env="production", anthropic_api_key="anthropic-key")
    monkeypatch.setattr(app_main, "_get_runtime_settings", lambda request: settings)
    provider = FakeProviderClient([])
    monkeypatch.setattr(app_main, "_get_http_client", lambda request: (provider, False))
    client = TestClient(app_main.app)

    response = client.post(
        "/api/anthropic/messages",
        json={"model": "claude-test", "max_tokens": 100, "messages": [{"role": "user", "content": "hi"}]},
    )

    assert response.status_code == 503
    assert response.json()["error"]["type"] == "auth_not_configured"
    assert provider.calls == []


def test_account_summary_selects_current_active_subscription(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = make_settings(
        tmp_path,
        supabase_url="https://project.supabase.co",
        supabase_anon_key="anon-key",
    )

    async def fake_user(request: Any, active_settings: Settings) -> AuthenticatedUser:
        return AuthenticatedUser(
            user_id="user-123",
            email="patrick@example.com",
            claims={"sub": "user-123"},
        )

    supabase = SupabaseMock([
        httpx.Response(
            200,
            json=[{
                "plan_code": "pro",
                "status": "active",
                "current_period_end": "2099-01-01T00:00:00Z",
            }],
        ),
        httpx.Response(200, json=[], headers={"content-range": "0-0/7"}),
    ])

    monkeypatch.setattr(app_main, "_get_runtime_settings", lambda request: settings)
    monkeypatch.setattr(app_main, "_resolve_authenticated_user", fake_user)
    monkeypatch.setattr(app_main, "_supabase_rest_request", supabase)
    client = TestClient(app_main.app)

    response = client.get("/api/account/summary", headers={"Authorization": "Bearer local-token"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["plan_code"] == "pro"
    assert payload["monthly_requests_used"] == 7
    subscription_params = supabase.calls[0]["params"]
    assert subscription_params["status"] == "in.(active,trialing)"
    assert subscription_params["order"] == "current_period_end.desc.nullslast"
    assert subscription_params["limit"] == "1"


def test_gemini_non_json_response_returns_explicit_502(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, gemini_api_key="gemini-key")
    provider = FakeProviderClient([httpx.Response(200, text="not json")])
    monkeypatch.setattr(app_main, "_get_runtime_settings", lambda request: settings)
    monkeypatch.setattr(app_main, "_get_http_client", lambda request: (provider, False))
    client = TestClient(app_main.app)

    response = client.post("/api/generate-image", json={"prompts": ["draw a clean palace"]})

    assert response.status_code == 502
    assert response.json()["error"]["type"] == "upstream_parse_error"
    assert len(provider.calls) == 1


def test_gemini_missing_inline_image_data_returns_explicit_502(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, gemini_api_key="gemini-key")
    provider = FakeProviderClient([
        httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"inlineData": {"mimeType": "image/png"}}]}}]},
        )
    ])
    monkeypatch.setattr(app_main, "_get_runtime_settings", lambda request: settings)
    monkeypatch.setattr(app_main, "_get_http_client", lambda request: (provider, False))
    client = TestClient(app_main.app)

    response = client.post("/api/generate-image", json={"prompts": ["draw a clean palace"]})

    assert response.status_code == 502
    assert response.json()["error"]["type"] == "no_image_in_response"


def test_frontend_uses_backend_owned_persistence_boundary() -> None:
    root = Path(__file__).resolve().parents[1]
    frontend_files = [
        root / "frontend" / "pages" / "forge.html",
        root / "frontend" / "pages" / "library.html",
        root / "frontend" / "scripts" / "palace-api.js",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in frontend_files)

    assert "supabaseClient.from" not in combined
    assert ".from('profiles')" not in combined
    assert ".from('palaces')" not in combined
    assert ".from('palace_versions')" not in combined
    assert "/api/profile/ensure" in combined
    assert "/api/palaces/save" in combined


def test_static_pages_load_shared_backend_persistence_script_before_inline_code() -> None:
    root = Path(__file__).resolve().parents[1]
    for page_name in ("forge.html", "library.html"):
        html = (root / "frontend" / "pages" / page_name).read_text(encoding="utf-8")
        shared_script_index = html.index("/scripts/palace-api.js")
        api_use_index = html.index("MnemorizedPalaceApi")

        assert shared_script_index < api_use_index
