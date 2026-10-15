from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app import main as app_main
from test_provider_and_static_boundaries import FakeProviderClient, make_settings


@pytest.mark.parametrize('source_available', [True, False])
def test_requested_grounding_preserves_late_source_details_or_blocks_provider(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, source_available: bool,
) -> None:
    settings = make_settings(
        tmp_path, anthropic_api_key='test-key', openai_api_key='test-key',
        supabase_url='https://project.supabase.co', supabase_anon_key='anon',
        supabase_service_role_key='service',
    )
    provider = FakeProviderClient([httpx.Response(200, json={'content': [{'type': 'text', 'text': 'ok'}], 'usage': {}})])

    async def retrieve(**kwargs: Any):
        return ([{
            'title': 'Sample topic', 'section_title': 'Sample topic',
            'chunk_text': 'Sample topic ' + ('Background details. ' * 100) + 'LATE_SOURCE_QUALIFIER',
            'similarity': 0.9, 'page_start': 4, 'page_end': 4,
        }] if source_available else []), {}

    monkeypatch.setattr(app_main, '_get_runtime_settings', lambda request: settings)
    monkeypatch.setattr(app_main, '_get_http_client', lambda request: (provider, False))
    monkeypatch.setattr(app_main, '_retrieve_medical_context', retrieve)
    monkeypatch.setattr(app_main, '_schedule_usage_event', lambda **kwargs: None)
    response = TestClient(app_main.app).post(
        '/api/anthropic/messages',
        headers={'x-evidence-grounding': 'true', 'x-evidence-topic': 'Sample topic'},
        json={'model': 'claude-test', 'max_tokens': 100, 'system': 'Use source evidence.',
              'messages': [{'role': 'user', 'content': 'Create the lesson.'}]},
    )

    if source_available:
        assert response.status_code == 200
        assert 'LATE_SOURCE_QUALIFIER' in provider.calls[0]['json']['system']
    else:
        assert response.status_code == 503
        assert provider.calls == []


@pytest.mark.parametrize('missing', ['configuration', 'topic', 'system'])
def test_requested_grounding_cannot_silently_skip_prerequisites(monkeypatch, tmp_path, missing):
    settings = make_settings(
        tmp_path, anthropic_api_key='test-key',
        openai_api_key='' if missing == 'configuration' else 'test-key',
        supabase_url='https://project.supabase.co', supabase_anon_key='anon',
        supabase_service_role_key='service',
    )
    provider = FakeProviderClient([])
    monkeypatch.setattr(app_main, '_get_runtime_settings', lambda request: settings)
    monkeypatch.setattr(app_main, '_get_http_client', lambda request: (provider, False))
    response = TestClient(app_main.app).post(
        '/api/anthropic/messages',
        headers={'x-evidence-grounding': 'true', 'x-evidence-topic': '' if missing == 'topic' else 'Sample topic'},
        json={'model': 'claude-test', 'max_tokens': 100,
              'system': '' if missing == 'system' else 'Use evidence.',
              'messages': [{'role': 'user', 'content': 'Create the lesson.'}]},
    )
    assert response.status_code == (503 if missing == 'configuration' else 400)
    assert provider.calls == []
