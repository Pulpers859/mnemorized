from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app import main as app_main
from test_provider_and_static_boundaries import FakeProviderClient, make_settings


def test_learner_instructions_do_not_discard_topic_continuation_pages():
    rows = [
        {'title': 'Reference', 'chunk_text': 'Pericarditis diagnostic features.', 'similarity': 0.65},
        {'title': 'Reference', 'chunk_text': 'Pericarditis treatment and disposition.', 'similarity': 0.60},
        {'title': 'Reference', 'chunk_text': 'Introductory medical student lesson with eight anchors on pneumonia.', 'similarity': 0.9},
    ]
    topic = 'Acute pericarditis: an introductory emergency medicine lesson for a medical student, eight anchors.'
    actual = app_main._topic_relevant_medical_rows(rows, topic, min_similarity=0.45)
    assert actual == rows[:2]


def test_learner_filter_keeps_multiword_clinical_matching_strict():
    rows = [
        {'chunk_text': 'Carbon monoxide exposure.', 'similarity': 0.7},
        {'chunk_text': 'Carbon dioxide retention in a medical student lesson.', 'similarity': 0.8},
        {'chunk_text': 'Opioid overdose: emergency treatment for medical students.', 'similarity': 0.9},
    ]
    actual = app_main._topic_relevant_medical_rows(rows,
        'Carbon monoxide: an introductory emergency medicine lesson for a medical student, eight anchors.', min_similarity=0.45)
    assert actual == rows[:1]


def test_instruction_only_query_cannot_match_arbitrary_evidence():
    rows = [{'chunk_text': 'Any source text.', 'similarity': 0.99}]
    assert app_main._topic_relevant_medical_rows(rows,
        'An introductory medical lesson for a student, eight anchors.', min_similarity=0.45) == []


def test_number_words_outside_output_count_phrase_remain_subject_terms():
    rows = [{'chunk_text': 'Eight affected structures.', 'similarity': 0.8},
            {'chunk_text': 'An unrelated introduction.', 'similarity': 0.9}]
    assert app_main._topic_relevant_medical_rows(rows, 'Eight', min_similarity=0.45) == rows[:1]


@pytest.mark.parametrize('source_available', [True, False])
@pytest.mark.parametrize('visual_preflight', [True, False])
def test_requested_grounding_preserves_late_source_details_or_blocks_provider(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, source_available: bool, visual_preflight: bool,
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
    monkeypatch.setattr(app_main, '_load_gemini_constitution', lambda: 'CANONICAL_PREFLIGHT_SENTINEL')
    response = TestClient(app_main.app).post(
        '/api/anthropic/messages',
        headers={'x-evidence-grounding': 'true', 'x-evidence-topic': 'Sample topic',
                 'x-visual-preflight': str(visual_preflight).lower()},
        json={'model': 'claude-test', 'max_tokens': 100, 'system': 'Use source evidence.',
              'messages': [{'role': 'user', 'content': 'Create the lesson.'}]},
    )

    if source_available:
        assert response.status_code == 200
        assert 'LATE_SOURCE_QUALIFIER' in provider.calls[0]['json']['system']
        assert ('CANONICAL_PREFLIGHT_SENTINEL' in provider.calls[0]['json']['system']) == visual_preflight
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


@pytest.mark.parametrize('missing', ['constitution', 'grounding'])
def test_visual_preflight_fails_closed_without_constitution_or_grounding(monkeypatch, tmp_path, missing):
    settings = make_settings(tmp_path, anthropic_api_key='test-key')
    provider = FakeProviderClient([])
    releases = []
    monkeypatch.setattr(app_main, '_get_runtime_settings', lambda request: settings)
    monkeypatch.setattr(app_main, '_get_http_client', lambda request: (provider, False))
    monkeypatch.setattr(app_main, '_load_gemini_constitution', lambda: '' if missing == 'constitution' else 'RULES')
    monkeypatch.setattr(app_main, '_release_quota_reservation', lambda *args: releases.append(True))
    response = TestClient(app_main.app).post('/api/anthropic/messages',
        headers={'x-visual-preflight': 'true', 'x-evidence-grounding': 'false' if missing == 'grounding' else 'true'},
        json={'model': 'claude-test', 'max_tokens': 100, 'system': 'Review.',
              'messages': [{'role': 'user', 'content': 'Review.'}]})
    assert response.status_code == 503
    assert provider.calls == []
    assert releases == [True]
