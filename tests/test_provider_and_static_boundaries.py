from __future__ import annotations

import os
from pathlib import Path
import struct
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app import main as app_main
from backend.app.auth import AuthenticatedUser
from backend.app.config import Settings, _load_env_file


def make_settings(
    tmp_path: Path,
    *,
    app_env: str = "development",
    anthropic_api_key: str = "",
    gemini_api_key: str = "",
    openai_api_key: str = "",
    supabase_url: str = "",
    supabase_anon_key: str = "",
    supabase_service_role_key: str = "",
    admin_emails: tuple[str, ...] = (),
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
        supabase_service_role_key=supabase_service_role_key,
        supabase_jwt_audience="authenticated",
        free_monthly_requests=40,
        pro_monthly_requests=400,
        team_monthly_requests=4000,
        billing_mode="beta",
        gemini_api_key=gemini_api_key,
        gemini_model="gemini-2.5-flash-image",
        openai_api_key=openai_api_key,
        openai_embedding_model="text-embedding-3-small",
        openai_embedding_dimensions=1536,
        plan_override_path=tmp_path / "plan_overrides.json",
        admin_emails=admin_emails,
    )


def test_env_file_overrides_stale_process_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("GEMINI_API_KEY=AIza-new-local-key\n", encoding="utf-8")
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.old-stale-key")

    _load_env_file(env_path)

    assert os.environ["GEMINI_API_KEY"] == "AIza-new-local-key"


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
    assert payload["plan_display_name"] == "Pro"
    assert payload["beta_mode"] is True
    assert payload["billing_enabled"] is False
    assert payload["upgrade_enabled"] is False
    assert payload["quota_unit_label"] == "AI requests"
    assert payload["monthly_requests_used"] == 7
    subscription_params = supabase.calls[0]["params"]
    assert subscription_params["status"] == "in.(active,trialing)"
    assert subscription_params["order"] == "current_period_end.desc.nullslast"
    assert subscription_params["limit"] == "1"


def test_public_config_exposes_explicit_beta_billing_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = make_settings(
        tmp_path,
        supabase_url="https://project.supabase.co",
        supabase_anon_key="anon-key",
        supabase_service_role_key="service-role-secret",
    )
    monkeypatch.setattr(app_main, "_get_runtime_settings", lambda request: settings)
    client = TestClient(app_main.app)

    response = client.get("/api/config/public")

    assert response.status_code == 200
    payload = response.json()
    assert payload["billing_mode"] == "beta"
    assert payload["beta_mode"] is True
    assert payload["billing_enabled"] is False
    assert payload["upgrade_enabled"] is False
    assert payload["upgrade_path_enabled"] is False
    assert payload["quota_unit_label"] == "AI requests"
    assert "private beta" in payload["billing_message"]
    assert "service-role-secret" not in response.text


def test_gemini_diagnostic_requires_admin_outside_dev(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = make_settings(
        tmp_path,
        app_env="production",
        gemini_api_key="gemini-key",
        supabase_url="https://project.supabase.co",
        supabase_anon_key="anon-key",
    )
    monkeypatch.setattr(app_main, "_get_runtime_settings", lambda request: settings)
    client = TestClient(app_main.app)

    response = client.get("/api/diagnose-gemini")

    assert response.status_code == 401
    assert response.json()["detail"] == "Sign in to access saved palaces."


def test_quota_exceeded_response_is_beta_safe_and_skips_provider(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = make_settings(
        tmp_path,
        gemini_api_key="gemini-key",
        supabase_url="https://project.supabase.co",
        supabase_anon_key="anon-key",
    )
    provider = FakeProviderClient([])

    async def fake_user(request: Any, active_settings: Settings) -> AuthenticatedUser:
        return AuthenticatedUser(
            user_id="user-123",
            email="patrick@example.com",
            claims={"sub": "user-123"},
        )

    async def fake_summary(**kwargs: Any) -> dict[str, Any]:
        return {
            "plan_code": "free",
            "plan_display_name": "Free Beta",
            "subscription_status": "inactive",
            "monthly_request_limit": 40,
            "monthly_requests_used": 40,
            "monthly_requests_remaining": 0,
            "period_started_at": "2026-06-01T00:00:00+00:00",
            "period_ends_at": "2026-07-01T00:00:00+00:00",
            "is_dev_override": False,
            **app_main._billing_context(settings),
        }

    monkeypatch.setattr(app_main, "_get_runtime_settings", lambda request: settings)
    monkeypatch.setattr(app_main, "_get_http_client", lambda request: (provider, False))
    monkeypatch.setattr(app_main, "_resolve_authenticated_user", fake_user)
    monkeypatch.setattr(app_main, "_get_subscription_and_usage_summary", fake_summary)
    client = TestClient(app_main.app)

    response = client.post(
        "/api/generate-image",
        headers={"Authorization": "Bearer local-token"},
        json={"prompts": ["draw a clean palace"]},
    )

    assert response.status_code == 402
    payload = response.json()
    assert payload["error"]["type"] == "quota_exceeded"
    assert "Billing is not active yet" in payload["error"]["message"]
    assert "Upgrade or wait" not in payload["error"]["message"]
    assert payload["plan"]["display_name"] == "Free Beta"
    assert payload["billing"]["mode"] == "beta"
    assert payload["billing"]["upgrade_path_enabled"] is False
    assert provider.calls == []


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


def test_gemini_upstream_error_schedules_usage_event(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = make_settings(
        tmp_path,
        gemini_api_key="gemini-key",
        supabase_url="https://project.supabase.co",
        supabase_anon_key="anon-key",
    )
    error_response = httpx.Response(500, json={"error": {"message": "temporary upstream failure"}})
    provider = FakeProviderClient([error_response, error_response, error_response])
    recorded_events: list[dict[str, Any]] = []

    async def fake_user(request: Any, active_settings: Settings) -> AuthenticatedUser:
        return AuthenticatedUser(
            user_id="user-123",
            email="patrick@example.com",
            claims={"sub": "user-123"},
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

    async def fake_persist_usage_event_background(**kwargs: Any) -> None:
        recorded_events.append(kwargs)

    import asyncio
    real_sleep = asyncio.sleep
    async def fast_sleep(seconds: float) -> None:
        await real_sleep(0)
    monkeypatch.setattr(asyncio, "sleep", fast_sleep)

    monkeypatch.setattr(app_main, "_get_runtime_settings", lambda request: settings)
    monkeypatch.setattr(app_main, "_get_http_client", lambda request: (provider, False))
    monkeypatch.setattr(app_main, "_resolve_authenticated_user", fake_user)
    monkeypatch.setattr(app_main, "_get_subscription_and_usage_summary", fake_summary)
    monkeypatch.setattr(
        app_main,
        "_persist_usage_event_background",
        fake_persist_usage_event_background,
    )

    with TestClient(app_main.app) as client:
        response = client.post(
            "/api/generate-image",
            headers={"Authorization": "Bearer local-token"},
            json={"prompts": ["draw a clean palace"]},
        )

    assert response.status_code == 502
    assert response.json()["error"]["type"] == "upstream_error"
    assert len(provider.calls) == 3, f"Expected 3 attempts (1 + 2 retries), got {len(provider.calls)}"
    assert len(recorded_events) == 1
    assert recorded_events[0]["status_code"] == 502
    assert recorded_events[0]["request_body"]["provider"] == "gemini"
    assert recorded_events[0]["request_body"]["prompts"] == 1


def test_validation_errors_do_not_echo_rejected_prompt() -> None:
    client = TestClient(app_main.app)
    rejected_prompt = "sensitive medical source " * 500

    response = client.post("/api/generate-image", json={"prompts": [rejected_prompt]})

    assert response.status_code == 422
    assert response.headers["x-request-id"]
    payload = response.json()
    assert payload["error"]["type"] == "validation_error"
    assert "sensitive medical source" not in response.text
    assert "input" not in response.text


def test_oversized_api_request_rejected_before_provider_call(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = make_settings(
        tmp_path,
        anthropic_api_key="anthropic-key",
    )
    settings = Settings(
        **{
            **settings.__dict__,
            "max_request_bytes": 20,
        }
    )
    provider = FakeProviderClient([])
    monkeypatch.setattr(app_main, "_get_runtime_settings", lambda request: settings)
    monkeypatch.setattr(app_main, "_get_http_client", lambda request: (provider, False))
    client = TestClient(app_main.app)

    response = client.post(
        "/api/anthropic/messages",
        json={
            "model": "claude-test",
            "max_tokens": 64,
            "messages": [{"role": "user", "content": "this valid body is too large"}],
        },
    )

    assert response.status_code == 413
    assert response.json()["error"]["type"] == "request_too_large"
    assert provider.calls == []


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
    assert "/api/medical-knowledge/quality-check" in combined
    assert "/api/medical-knowledge/context" in combined
    assert "medical.medical_knowledge_chunks" not in combined
    assert "match_medical_knowledge_chunks" not in combined


def test_frontend_surfaces_beta_quota_language() -> None:
    root = Path(__file__).resolve().parents[1]
    forge_state = (root / "frontend" / "scripts" / "forge-state.js").read_text(encoding="utf-8")
    forge_auth = (root / "frontend" / "scripts" / "forge-auth.js").read_text(encoding="utf-8")
    library = (root / "frontend" / "pages" / "library.html").read_text(encoding="utf-8")

    assert "Monthly beta quota exceeded" in forge_state
    assert "Billing and upgrades are not active yet" in forge_state
    assert "Mnemorized is in private beta" in forge_auth
    assert "Monthly AI Requests" in library
    assert "Free Beta" in library


def test_static_pages_load_shared_backend_persistence_script_before_inline_code() -> None:
    root = Path(__file__).resolve().parents[1]
    library = (root / "frontend" / "pages" / "library.html").read_text(encoding="utf-8")
    forge = (root / "frontend" / "pages" / "forge.html").read_text(encoding="utf-8")
    admin = (root / "frontend" / "pages" / "admin.html").read_text(encoding="utf-8")

    assert library.index("/scripts/palace-api.js") < library.index("MnemorizedPalaceApi")
    assert forge.index("/scripts/palace-api.js") < forge.index("/scripts/forge-auth.js")
    assert forge.index("/scripts/forge-input-builder.js") < forge.index("/scripts/forge-pipeline.js")
    assert admin.index("/scripts/palace-api.js") < admin.index("MnemorizedAdminApi")


def test_admin_dashboard_wires_protected_diagnostics_flow() -> None:
    root = Path(__file__).resolve().parents[1]
    admin = (root / "frontend" / "pages" / "admin.html").read_text(encoding="utf-8")
    shared = (root / "frontend" / "scripts" / "palace-api.js").read_text(encoding="utf-8")
    backend = (root / "backend" / "app" / "main.py").read_text(encoding="utf-8")

    assert "@app.get(\"/admin\")" in backend
    assert "@app.get(\"/api/admin/diagnostics\")" in backend
    assert "Admin access is required." in backend
    assert "SUPABASE_SERVICE_ROLE_KEY is required for admin diagnostics." in backend
    assert "window.MnemorizedAdminApi" in shared
    assert "/api/admin/diagnostics" in shared
    assert "/api/admin/catalog-seeds" in shared
    assert "/api/admin/catalog-seeds/publish" in shared
    assert "MnemorizedAdminApi.diagnostics(token())" in admin
    assert "MnemorizedAdminApi.catalogSeeds(token())" in admin
    assert "MnemorizedAdminApi.publishCatalogSeed(token(), slug)" in admin
    assert "Provider Failures" in admin
    assert "Catalog Publish History" in admin
    assert "Catalog Seeds" in admin
    assert "seedPublishPending" in admin
    assert "supabaseClient.auth.signInWithPassword" in admin


def test_production_cors_does_not_allow_wildcard(tmp_path: Path) -> None:
    settings = make_settings(
        tmp_path,
        app_env="production",
        supabase_url="https://project.supabase.co",
        supabase_anon_key="anon-key",
    )

    assert settings.cors_origins == ("*",)
    assert settings.cors_allowed_origins == ("http://127.0.0.1:8001",)


def test_demo_mode_status_matches_actual_output() -> None:
    root = Path(__file__).resolve().parents[1]
    pipeline = (root / "frontend" / "scripts" / "forge-pipeline.js").read_text(encoding="utf-8")

    assert "✓ Image prompts ready" in pipeline
    assert "✓ Scene illustration in progress" not in pipeline


def test_forge_does_not_label_auth_failures_as_network_cors() -> None:
    root = Path(__file__).resolve().parents[1]
    html = (root / "frontend" / "pages" / "forge.html").read_text(encoding="utf-8")

    assert "Fetch failed (network/CORS)" not in html


def test_forge_prioritizes_direct_topic_entry_over_upload() -> None:
    root = Path(__file__).resolve().parents[1]
    html = (root / "frontend" / "pages" / "forge.html").read_text(encoding="utf-8")

    topic_index = html.index('id="topic"')
    upload_index = html.index('id="upload-zone"')

    assert topic_index < upload_index
    assert '<details class="optional-upload" id="optional-upload">' in html
    assert '<div id="config-wrap" style="display:block;">' in html
    assert '<div id="forge-wrap" style="display:block;">' in html
    assert "manual-bypass" not in html


def test_forge_guided_input_builder_writes_existing_topic_field() -> None:
    root = Path(__file__).resolve().parents[1]
    html = (root / "frontend" / "pages" / "forge.html").read_text(encoding="utf-8")
    builder = (root / "frontend" / "scripts" / "forge-input-builder.js").read_text(encoding="utf-8")
    pipeline = (root / "frontend" / "scripts" / "forge-pipeline.js").read_text(encoding="utf-8")

    builder_index = html.index('id="guided-input-builder"')
    topic_index = html.index('id="topic"')
    upload_index = html.index('id="upload-zone"')

    assert builder_index < topic_index < upload_index
    assert '<details class="input-builder" id="guided-input-builder">' in html
    assert "Guided Input Builder" in html
    assert "Draft Into Text Box" in html
    assert "Only the final Section I text box is sent for generation." in html
    assert "No patient-identifying information" in html
    assert "const INPUT_BUILDER_PRESETS" in builder
    assert "function selectBuilderPreset" in builder
    assert "function draftGuidedTopic" in builder
    assert "function clearGuidedBuilder" in builder
    assert "topicField.value" in builder
    assert "document.getElementById('topic')" in builder
    assert "fetch(" not in builder
    assert "claudeFetch" not in builder
    assert "supabase" not in builder.lower()
    assert "Mnemorized" not in builder
    assert "Uploaded or pasted content may be sent to AI providers" in html
    assert "document.getElementById('topic').value.trim()" in pipeline
    assert "builder-topic" not in pipeline


def test_forge_shows_medical_safety_privacy_guardrails() -> None:
    root = Path(__file__).resolve().parents[1]
    html = (root / "frontend" / "pages" / "forge.html").read_text(encoding="utf-8")
    pipeline = (root / "frontend" / "scripts" / "forge-pipeline.js").read_text(encoding="utf-8")

    assert 'id="content-safety-note"' in html
    assert "Do not enter patient-identifying information." in html
    assert "Use educational/source material only." in html
    assert "Uploaded or pasted content may be sent to AI providers for generation." in html
    assert "Private medical reference retrieval uses backend-only access." in html
    assert "upload-privacy-note" in html
    assert "Do not include patient-identifying information." in pipeline


def test_forge_story_output_avoids_nested_scroll_traps() -> None:
    root = Path(__file__).resolve().parents[1]
    html = (root / "frontend" / "pages" / "forge.html").read_text(encoding="utf-8")

    assert ".story-table-scroll {\n  overflow: visible;" in html
    assert "position: sticky" not in html
    assert '<aside class="story-summary-panel">' in html
    assert 'class="legend story-side-review" id="review-wrap"' in html
    assert "story-review-drawer" not in html


def test_forge_wires_medical_quality_gate_after_story_generation() -> None:
    root = Path(__file__).resolve().parents[1]
    html = (root / "frontend" / "pages" / "forge.html").read_text(encoding="utf-8")
    pipeline = (root / "frontend" / "scripts" / "forge-pipeline.js").read_text(encoding="utf-8")
    auth = (root / "frontend" / "scripts" / "forge-auth.js").read_text(encoding="utf-8")
    shared = (root / "frontend" / "scripts" / "palace-api.js").read_text(encoding="utf-8")

    assert 'id="stage-quality"' in html
    assert 'id="status-quality"' in html
    assert 'id="quality-result"' in html
    assert 'id="detail-story"' in html
    assert 'id="detail-quality"' in html
    assert 'id="detail-prompt"' in html
    assert '<span class="stage-num">02</span>\n        <span class="stage-title">Medical Quality Gate</span>' in html
    assert '<span class="stage-num">03</span>\n        <span class="stage-title">Scene Illustration</span>' in html
    assert "function setStageDetail" in (root / "frontend" / "scripts" / "forge-state.js").read_text(encoding="utf-8")
    assert "Retrieving backend-only reference snippets" in auth
    assert "await runMedicalQualityGate(storyData, coreConcepts);" in pipeline
    assert "Demo mode uses built-in sample content" in pipeline
    assert "function runMedicalQualityGate" in auth
    assert "function repairCurrentPalaceWithMedicalEvidence" in auth
    assert "Repair with Medical Evidence" in auth
    assert "MnemorizedMedicalApi.context" in auth
    assert "Medical repair complete. Review the updated script" in auth
    assert "No relevant private source found for this topic." in auth
    assert "No source match" in auth
    assert "function rebuildImagePromptsForStory" in pipeline
    assert "✓ Rebuilt from repaired script" in pipeline
    assert "medicalKnowledgeEnabled" in auth
    assert "quality_gate: currentQualityGateData" in auth
    assert "window.MnemorizedMedicalApi" in shared


def test_forge_story_generation_uses_shared_parser_and_validator() -> None:
    root = Path(__file__).resolve().parents[1]
    pipeline = (root / "frontend" / "scripts" / "forge-pipeline.js").read_text(encoding="utf-8")
    auth = (root / "frontend" / "scripts" / "forge-auth.js").read_text(encoding="utf-8")

    assert "function validateStoryData" in auth
    assert "const storyValidation = validateStoryData(storyData);" in pipeline
    assert "storyData = parseStoryXml(txt);" in pipeline
    assert "ANCHOR is the clinical fact only" in pipeline
    assert "anchor contains mnemonic/narration language" in auth
    assert "const scene_title   = extractXmlTag(txt, 'scene_title');" not in pipeline
    assert "const voRaw = extractAllXmlTags(txt, 'vo_line');" not in pipeline


def test_forge_story_prompt_prioritizes_masterful_visual_mnemonic_cues() -> None:
    root = Path(__file__).resolve().parents[1]
    pipeline = (root / "frontend" / "scripts" / "forge-pipeline.js").read_text(encoding="utf-8")
    auth = (root / "frontend" / "scripts" / "forge-auth.js").read_text(encoding="utf-8")

    assert "VISUAL MNEMONIC DESIGN — THIS IS THE HEART OF THE PRODUCT" in pipeline
    assert "ENCODING HIERARCHY" in pipeline
    assert "SOUND-ALIKE (strongest)" in pipeline
    assert "LOOK-ALIKE" in pipeline
    assert "FUNCTIONAL ANALOGY" in pipeline
    assert "CONTRAST/THRESHOLD" in pipeline
    assert "SPATIAL" in pipeline
    assert "LABELED TEXT (weakest — LAST RESORT)" in pipeline
    assert "SILHOUETTE TEST" in pipeline
    assert "CHARACTER DESIGN (encouraged)" in pipeline
    assert "OBJECT INTERACTION = CLINICAL RELATIONSHIP" in pipeline
    assert "The setting is a spatial memory map, not a backdrop." in pipeline
    assert "Contact, blocking, containment, distance, scale, elevation, and sequence" in pipeline
    assert "one coherent static map with uncluttered anchor zones" in pipeline
    assert "Plain checklists, generic posters, ordinary clipboards" in pipeline
    assert "silhouette test" in pipeline
    assert "HOOK:" in pipeline
    assert "do not reuse named scenes, recurring characters, or proprietary symbols" in pipeline.lower()
    assert "Use visual-mnemonic design principles only; do not copy named scenes" in auth
    assert "missing HOOK; visual cue quality may degrade" in auth
    assert "HOOK should start with sound-alike, look-alike, functional, contrast, or spatial" in auth
    assert "Hook: ${v.hook}" in pipeline
    assert "Encodes: ${v.anchor}" in pipeline
    assert 'The words "Hook" and "Encodes" are invisible design guidance only' in pipeline
    assert "Preserve clear spatial hierarchy" in pipeline
    assert "Design the room as a clear spatial memory map" in pipeline
    assert "Setting must be a phonetic pun" not in pipeline
    assert "MUST be a PHONETIC PUN" not in pipeline


def test_forge_save_has_visible_success_confirmation() -> None:
    root = Path(__file__).resolve().parents[1]
    auth = (root / "frontend" / "scripts" / "forge-auth.js").read_text(encoding="utf-8")

    assert "Saved to Library:" in auth
    assert "saveBtn.textContent = 'Saving...'" in auth
    assert "primarySaveBtn.textContent = 'Saved'" in auth


def test_library_catalog_has_loading_error_and_empty_states() -> None:
    root = Path(__file__).resolve().parents[1]
    html = (root / "frontend" / "pages" / "library.html").read_text(encoding="utf-8")

    assert "let catalogLoading = false;" in html
    assert "let catalogError = '';" in html
    assert "Loading curated catalog..." in html
    assert "Catalog could not load:" in html
    assert "No catalog palaces match this tag yet." in html
    assert "No catalog palaces match that search yet." in html
    assert "No curated palaces are published yet." in html


def test_library_inline_handlers_escape_palace_ids() -> None:
    root = Path(__file__).resolve().parents[1]
    html = (root / "frontend" / "pages" / "library.html").read_text(encoding="utf-8")
    shared = (root / "frontend" / "scripts" / "palace-api.js").read_text(encoding="utf-8")

    assert "function escapeJsString" in shared
    assert "escapeJsString" in html
    assert "onclick=\"renamePalace('${palaceId}')\"" in html
    assert "onclick=\"deletePalace('${palaceId}')\"" in html


def test_catalog_schema_does_not_grant_browser_write_policies() -> None:
    root = Path(__file__).resolve().parents[1]
    schema = (root / "backend" / "sql" / "supabase_schema.sql").read_text(encoding="utf-8")
    catalog_block = schema.split("Shared palace catalog", 1)[1].split("Auto-update updated_at", 1)[0]

    assert "revoke all on public.catalog_palaces from anon, authenticated" in catalog_block
    assert "grant select on public.catalog_palaces to anon, authenticated" in catalog_block
    assert "for insert" not in catalog_block
    assert "for delete" not in catalog_block
    assert "auth.role()" not in catalog_block
    assert "idx_catalog_palaces_published_by" in catalog_block


def test_supabase_schema_hardens_rls_and_trigger_functions() -> None:
    root = Path(__file__).resolve().parents[1]
    schema = (root / "backend" / "sql" / "supabase_schema.sql").read_text(encoding="utf-8")

    assert "revoke execute on function public.handle_new_user() from public, anon, authenticated" in schema
    assert "revoke execute on function public.set_updated_at() from public, anon, authenticated" in schema
    assert "set search_path = public" in schema
    assert "using (auth.uid()" not in schema
    assert "with check (auth.uid()" not in schema
    assert "with check ((select auth.uid()) = id)" in schema
    assert "with check ((select auth.uid()) = user_id)" in schema


def test_medical_knowledge_schema_is_private_service_role_only() -> None:
    root = Path(__file__).resolve().parents[1]
    schema = (root / "backend" / "sql" / "supabase_schema.sql").read_text(encoding="utf-8")
    medical_block = schema.split("Private medical knowledge base", 1)[1]

    assert "create schema if not exists medical" in medical_block
    assert "alter table medical.medical_sources enable row level security" in medical_block
    assert "alter table medical.medical_knowledge_chunks enable row level security" in medical_block
    assert "medical_sources_no_browser_access" in medical_block
    assert "medical_chunks_no_browser_access" in medical_block
    assert "using (false)" in medical_block
    assert "revoke all on schema medical from public, anon, authenticated" in medical_block
    assert "revoke all on medical.medical_knowledge_chunks from public, anon, authenticated" in medical_block
    assert "grant select, insert, update, delete on medical.medical_knowledge_chunks to service_role" in medical_block
    assert "security definer" in medical_block
    assert "revoke execute on function public.match_medical_knowledge_chunks" in medical_block
    assert "grant execute on function public.match_medical_knowledge_chunks" in medical_block
    assert "to service_role" in medical_block
    assert "grant select on medical.medical_knowledge_chunks to anon" not in medical_block
    assert "grant select on medical.medical_knowledge_chunks to authenticated" not in medical_block


def test_medical_env_examples_are_placeholder_only() -> None:
    root = Path(__file__).resolve().parents[1]
    example = (root / "backend" / ".env.example").read_text(encoding="utf-8")

    assert "OPENAI_API_KEY=replace-with-local-openai-key" in example
    assert "OPENAI_EMBEDDING_MODEL=text-embedding-3-small" in example
    assert "OPENAI_EMBEDDING_DIMENSIONS=1536" in example
    assert "sk-" not in example


def test_medical_ingestion_requires_explicit_openai_confirmation() -> None:
    root = Path(__file__).resolve().parents[1]
    tool = (root / "tools" / "ingest_medical_knowledge.py").read_text(encoding="utf-8")

    assert "--confirm-send-to-openai" in tool
    assert "Refusing to upload private source text" in tool
    assert "p_source_path\": path.name" in tool


def test_service_worker_does_not_cache_html_or_itself() -> None:
    root = Path(__file__).resolve().parents[1]
    sw = (root / "frontend" / "sw.js").read_text(encoding="utf-8")
    forge_pipeline = (root / "frontend" / "scripts" / "forge-pipeline.js").read_text(encoding="utf-8")

    static_block = sw.split("];", 1)[0]
    assert "'/forge'" not in static_block
    assert "'/library'" not in static_block
    assert "'/admin'" not in static_block
    assert "'/'" not in static_block
    assert "url.pathname === '/sw.js'" in sw
    assert "fetch(event.request, { cache: 'no-store' })" in sw
    assert "updateViaCache: 'none'" in forge_pipeline


def test_pwa_icon_is_optimized_for_install_surface() -> None:
    root = Path(__file__).resolve().parents[1]
    icon = root / "frontend" / "assets" / "profile-pic.png"
    data = icon.read_bytes()
    width, height = struct.unpack(">II", data[16:24])

    assert len(data) < 1_000_000
    assert (width, height) == (512, 512)
