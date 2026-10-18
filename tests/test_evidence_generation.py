from pathlib import Path
import asyncio
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app import main as app_main
from test_provider_and_static_boundaries import FakeProviderClient, make_settings


CONTRACT_START = 'BEGIN ACTIVE PRE-RENDER CONTRACT'
CONTRACT_END = 'END ACTIVE PRE-RENDER CONTRACT'
ACTIVE_CONTRACT = 'CANONICAL_PREFLIGHT_SENTINEL\nPreserve source qualifiers.'
CANONICAL_CONSTITUTION = (
    f'HISTORICAL_PREFIX_SENTINEL\n{CONTRACT_START}\n\n'
    f'{ACTIVE_CONTRACT}\n\n{CONTRACT_END}\nHISTORICAL_SUFFIX_SENTINEL'
)
INVALID_CONSTITUTIONS = [
    pytest.param('', id='missing-file-content'),
    pytest.param('Historical rules only.', id='missing-both-markers'),
    pytest.param(f'Rules\n{CONTRACT_END}', id='missing-start'),
    pytest.param(f'{CONTRACT_START}\nRules', id='missing-end'),
    pytest.param(f'{CONTRACT_END}\nRules\n{CONTRACT_START}', id='reversed'),
    pytest.param(f'{CONTRACT_START}{CONTRACT_END}', id='empty'),
    pytest.param(f'{CONTRACT_START}\n \t\r\n{CONTRACT_END}', id='whitespace-only'),
    pytest.param(f'{CONTRACT_START}\n{CANONICAL_CONSTITUTION}', id='duplicate-start'),
    pytest.param(f'{CANONICAL_CONSTITUTION}\n{CONTRACT_END}', id='duplicate-end'),
    pytest.param(CANONICAL_CONSTITUTION * 2, id='duplicate-block'),
    pytest.param(CANONICAL_CONSTITUTION.lower(), id='nonexact-markers'),
]


@pytest.fixture(autouse=True)
def isolate_rate_limiter(monkeypatch):
    monkeypatch.setattr(app_main.app.state, 'rate_limiter', None, raising=False)


def test_visual_preflight_contract_extracts_only_trimmed_active_rules(monkeypatch):
    monkeypatch.setattr(app_main, '_load_gemini_constitution', lambda: CANONICAL_CONSTITUTION)
    assert app_main._load_visual_preflight_contract() == ACTIVE_CONTRACT


@pytest.mark.parametrize('constitution', INVALID_CONSTITUTIONS)
def test_visual_preflight_contract_rejects_invalid_boundaries(monkeypatch, constitution):
    monkeypatch.setattr(app_main, '_load_gemini_constitution', lambda: constitution)
    assert app_main._load_visual_preflight_contract() == ''


def test_active_contract_extraction_preserves_full_image_director_constitution(monkeypatch, tmp_path):
    path = tmp_path / 'constitution.txt'
    path.write_text(CANONICAL_CONSTITUTION, encoding='utf-8')
    monkeypatch.setattr(app_main, 'GEMINI_CONSTITUTION_PATH', path)

    assert app_main._load_visual_preflight_contract() == ACTIVE_CONTRACT
    assert app_main._load_gemini_constitution() == CANONICAL_CONSTITUTION
    assert CANONICAL_CONSTITUTION in app_main._gemini_prompt_director_system_prompt()
    assert path.read_text(encoding='utf-8') == CANONICAL_CONSTITUTION


def test_learner_instructions_do_not_discard_topic_continuation_pages():
    rows = [
        {'title': 'Reference', 'chunk_text': 'Pericarditis diagnostic features.', 'similarity': 0.65},
        {'title': 'Reference', 'chunk_text': 'Pericarditis treatment and disposition.', 'similarity': 0.60},
        {'title': 'Reference', 'chunk_text': 'Introductory medical student lesson with eight anchors on pneumonia.', 'similarity': 0.9},
    ]
    topic = 'Acute pericarditis: an introductory emergency medicine lesson for a medical student, eight anchors.'
    actual = app_main._topic_relevant_medical_rows(rows, topic, min_similarity=0.45)
    assert actual == rows[:2]


@pytest.mark.parametrize('topic,expected', [
    ('Neuroleptic malignant syndrome: an introductory emergency medicine lesson for a medical student, eight anchors.', 'Neuroleptic malignant syndrome'),
    ('Acute bacterial meningitis: an introductory emergency medicine lesson for a medical student, eight anchors.', 'Acute bacterial meningitis'),
    ('Shock: a lesson for a resident, 8 anchors.', 'Shock'),
    ('Topic: diabetic ketoacidosis\nMust include potassium before insulin.', 'Topic: diabetic ketoacidosis\nMust include potassium before insulin.'),
    ('Shock: an introductory emergency medicine lesson for a medical student, eight anchors. Include reassessment.', 'Shock: an introductory emergency medicine lesson for a medical student, eight anchors. Include reassessment.'),
    ('Acute angle-closure glaucoma diagnosis and treatment', 'Acute angle-closure glaucoma diagnosis and treatment'),
    (': a lesson for a resident, 8 anchors.', ': a lesson for a resident, 8 anchors.'),
])
def test_retrieval_strips_only_complete_trailing_format_suffix(topic, expected):
    assert app_main._medical_retrieval_query(topic) == expected


def test_embedding_and_hybrid_search_share_the_same_clinical_query(monkeypatch):
    observed = {}

    async def embedding(**kwargs):
        observed['embedding'] = kwargs['text']
        return [0.1, 0.2], {'tokens': 2}

    async def retrieve(**kwargs):
        observed['hybrid'] = kwargs['json_body']['p_query_text']
        return httpx.Response(200, json=[])

    monkeypatch.setattr(app_main, '_create_openai_embedding', embedding)
    monkeypatch.setattr(app_main, '_supabase_rest_request', retrieve)
    topic = 'Neuroleptic malignant syndrome: an introductory emergency medicine lesson for a medical student, eight anchors.'
    rows, usage = asyncio.run(app_main._retrieve_medical_context(request=object(),
        settings=SimpleNamespace(medical_knowledge_configured=True), query_text=topic, max_chunks=6))
    assert observed == {'embedding': 'Neuroleptic malignant syndrome', 'hybrid': 'Neuroleptic malignant syndrome'}
    assert rows == [] and usage == {'tokens': 2}


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
    source_text = 'Sample topic ' + ('Background details. ' * 500) + 'LATE_SOURCE_QUALIFIER'
    releases = []

    async def retrieve(**kwargs: Any):
        return ([{
            'title': 'Sample topic', 'section_title': 'Sample topic',
            'chunk_text': source_text,
            'similarity': 0.9, 'page_start': 4, 'page_end': 4,
        }] if source_available else []), {}

    monkeypatch.setattr(app_main, '_get_runtime_settings', lambda request: settings)
    monkeypatch.setattr(app_main, '_get_http_client', lambda request: (provider, False))
    monkeypatch.setattr(app_main, '_retrieve_medical_context', retrieve)
    monkeypatch.setattr(app_main, '_schedule_usage_event', lambda **kwargs: None)
    monkeypatch.setattr(app_main, '_load_gemini_constitution', lambda: CANONICAL_CONSTITUTION)
    monkeypatch.setattr(app_main, '_release_quota_reservation', lambda *args: releases.append(True))
    response = TestClient(app_main.app).post(
        '/api/anthropic/messages',
        headers={'x-evidence-grounding': 'true', 'x-evidence-topic': 'Sample topic',
                 'x-visual-preflight': str(visual_preflight).lower()},
        json={'model': 'claude-test', 'max_tokens': 100, 'system': 'Use source evidence.',
              'messages': [{'role': 'user', 'content': 'Create the lesson.'}]},
    )

    if source_available:
        assert response.status_code == 200
        assert len(provider.calls) == 1
        system = provider.calls[0]['json']['system']
        assert source_text in system
        assert (ACTIVE_CONTRACT in system) == visual_preflight
        assert 'HISTORICAL_PREFIX_SENTINEL' not in system
        assert 'HISTORICAL_SUFFIX_SENTINEL' not in system
        assert CONTRACT_START not in system
        assert CONTRACT_END not in system
    else:
        assert response.status_code == 503
        assert provider.calls == []
        assert releases == [True]


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


@pytest.mark.parametrize('missing', ['constitution', 'grounding', 'system'])
def test_visual_preflight_fails_closed_without_constitution_or_grounding(monkeypatch, tmp_path, missing):
    settings = make_settings(tmp_path, anthropic_api_key='test-key')
    provider = FakeProviderClient([])
    releases = []
    monkeypatch.setattr(app_main, '_get_runtime_settings', lambda request: settings)
    monkeypatch.setattr(app_main, '_get_http_client', lambda request: (provider, False))
    monkeypatch.setattr(app_main, '_load_gemini_constitution',
                        lambda: '' if missing == 'constitution' else CANONICAL_CONSTITUTION)
    monkeypatch.setattr(app_main, '_release_quota_reservation', lambda *args: releases.append(True))
    response = TestClient(app_main.app).post('/api/anthropic/messages',
        headers={'x-visual-preflight': 'true', 'x-evidence-grounding': 'false' if missing == 'grounding' else 'true'},
        json={'model': 'claude-test', 'max_tokens': 100, 'system': '' if missing == 'system' else 'Review.',
              'messages': [{'role': 'user', 'content': 'Review.'}]})
    assert response.status_code == 503
    assert provider.calls == []
    assert releases == [True]


@pytest.mark.parametrize('constitution', INVALID_CONSTITUTIONS)
def test_invalid_preflight_contract_releases_quota_before_retrieval_or_provider(
    monkeypatch, tmp_path, constitution,
):
    settings = make_settings(
        tmp_path, anthropic_api_key='test-key', openai_api_key='test-key',
        supabase_url='https://project.supabase.co', supabase_anon_key='anon',
        supabase_service_role_key='service',
    )
    provider = FakeProviderClient([])
    quota_events = []

    def reserve(request, user, summary):
        quota_events.append('reserve')
        return True, summary

    async def unexpected_retrieval(**kwargs):
        pytest.fail('Invalid preflight contracts must block before source retrieval.')

    monkeypatch.setattr(app_main, '_get_runtime_settings', lambda request: settings)
    monkeypatch.setattr(app_main, '_get_http_client', lambda request: (provider, False))
    monkeypatch.setattr(app_main, '_load_gemini_constitution', lambda: constitution)
    monkeypatch.setattr(app_main, '_retrieve_medical_context', unexpected_retrieval)
    monkeypatch.setattr(app_main, '_reserve_quota_if_needed', reserve)
    monkeypatch.setattr(app_main, '_release_quota_reservation', lambda *args: quota_events.append('release'))

    response = TestClient(app_main.app).post(
        '/api/anthropic/messages',
        headers={'x-visual-preflight': 'true', 'x-evidence-grounding': 'true',
                 'x-evidence-topic': 'Sample topic'},
        json={'model': 'claude-test', 'max_tokens': 100, 'system': 'Review.',
              'messages': [{'role': 'user', 'content': 'Review.'}]},
    )

    assert response.status_code == 503
    assert provider.calls == []
    assert quota_events == ['reserve', 'release']
