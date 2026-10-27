"""Offline adversarial tests for the promoted audited review algorithms."""

from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'chapter_cue_review_payloads', ROOT / 'tools/chapter_cue_review_payloads.py')
payloads = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(payloads)


def record(identifier='alpha', scope='head only', status='retain_candidate', term=None):
    return {'ref': 'docs/chapter-12A-cue-audit.json#' + identifier,
            'term': identifier if term is None else term,
            'status': status, 'cue_scope': scope}


def query(selected=(), held=(), selected_count=None, held_count=None, host='host'):
    return {'host': host,
            'selected_count': len(selected) if selected_count is None else selected_count,
            'held_count': len(held) if held_count is None else held_count,
            'selected_forms': [{'cue': 'Exact cue', 'records': list(selected)}] if selected else [],
            'held_forms': [{'cue': 'Exact cue', 'records': list(held)}] if held else []}


def semantic_source():
    row = {'row': 0, 'term': 'Example', 'association_status': 'hold', 'prior': None,
           'cue': None, 'attempted_cue': 'literal | alpha \u03b1',
           'cue_scope': 'not a mechanism', 'reason': 'Keep distinct scope.',
           'association_comparison': 'No admitted prior.',
           'new_field': {'literal': [False, None, 0, '\n']}}
    return 'prefix\n' + json.dumps(row, ensure_ascii=True) + '\nTOTAL_SEMANTIC_ROWS 1\nnotes|unchanged\n'


def test_semantic_exact_roundtrip_and_input_immutability():
    source = semantic_source()
    assert payloads.decode_semantic_view(payloads.encode_semantic_view(source)) == source
    assert payloads.encode_semantic_view('TOTAL_SEMANTIC_ROWS 0\n') == 'TOTAL_SEMANTIC_ROWS 0\n'


@pytest.mark.parametrize('body', [
    '["row","row"]}\n[0,1]\n' + payloads.END + '\n',
    '["row"]}\n[0,1]\n' + payloads.END + '\n',
    '["row"]}\n[0]\n',
    '{"row":1}}\n[0]\n' + payloads.END + '\n',
    '["row"],"extra":true}\n[0]\n' + payloads.END + '\n',
    '["row"],"$semantic_columns":["row"]}\n[0]\n' + payloads.END + '\n',
    '["row"]}\n[NaN]\n' + payloads.END + '\n',
])
def test_semantic_malformed_rejected(body):
    with pytest.raises(ValueError):
        payloads.decode_semantic_view(payloads.HEADER + body)


def test_semantic_reserved_and_noncanonical_layout_rejected():
    for source in (payloads.HEADER, payloads.END,
                   semantic_source().replace(': 0', ':  0', 1)):
        with pytest.raises(ValueError):
            payloads.encode_semantic_view(source)


@pytest.mark.parametrize('membership', ['selected_forms', 'held_forms'])
def test_empty_evidence_form_is_rejected_without_silent_cue_loss(membership):
    source = query()
    source[membership] = [{'cue': 'An exact cue with no displayed records', 'records': []}]
    with pytest.raises(ValueError, match='Empty evidence form'):
        payloads.encode_evidence([source])


def test_evidence_preserves_status_scope_override_duplicates_and_order():
    first = record('stable-id', scope=None, term='Different lexical term')
    source = [query([first, deepcopy(first), record('b', 'modifier'),
                     record('c', status='reuse_candidate')], [record(status='hold')],
                    selected_count=9), query(host='zero'), query(selected_count=8, host='truncated')]
    frozen = deepcopy(source)
    packet = payloads.encode_evidence(source)
    actual = payloads.decode_evidence(packet)
    assert source == frozen
    assert [q['host'] for q in actual] == ['host', 'zero', 'truncated']
    assert [q['selected_count'] for q in actual] == [9, 0, 8]
    assert packet['queries'][0][3][0][3] == [
        ['12A#stable-id', 'Different lexical term'], ['12A#stable-id', 'Different lexical term']]
    assert actual[0]['selected'][0] == actual[0]['selected'][1]
    assert actual[0]['selected'][0]['cue_scope'] is None
    assert actual[0]['held'][0]['status'] == 'hold'


@pytest.mark.parametrize('level', ['query', 'form', 'record', 'packet'])
def test_unknown_fields_rejected(level):
    source = query([record()])
    if level == 'packet':
        packet = payloads.encode_evidence([source])
        packet['unknown'] = True
        with pytest.raises(ValueError):
            payloads.decode_evidence(packet)
        return
    target = {'query': source, 'form': source['selected_forms'][0],
              'record': source['selected_forms'][0]['records'][0]}[level]
    target['unknown'] = 'must not disappear'
    with pytest.raises(ValueError):
        payloads.encode_evidence([source])


@pytest.mark.parametrize('count', [-1, True, 1.0, '1', None])
def test_invalid_counts_rejected_on_encode(count):
    source = query()
    source['selected_count'] = count
    with pytest.raises(ValueError):
        payloads.encode_evidence([source])


@pytest.mark.parametrize('ref', ['dangling', '#a', '12#', '../12#a', '12/other#a',
                                 '12\\other#a', '0#a', '12# ', [], ['12#a'],
                                 ['12#a', None], ['12#a', 'term', 'extra'], 42])
def test_invalid_references_rejected(ref):
    packet = payloads.encode_evidence([query([record()])])
    packet['queries'][0][3][0][3] = [ref]
    with pytest.raises(ValueError):
        payloads.decode_evidence(packet)


def test_missing_scope_bad_membership_schema_and_excess_display_rejected():
    missing = record()
    del missing['cue_scope']
    for source in (query([missing]), query([record(status='hold')]),
                   query(held=[record()]), query([record()], selected_count=0)):
        with pytest.raises(ValueError):
            payloads.encode_evidence([source])
    for key in ('query_columns', 'card_columns'):
        packet = payloads.encode_evidence([query()])
        packet[key].reverse()
        with pytest.raises(ValueError):
            payloads.decode_evidence(packet)


@pytest.mark.parametrize('mutation', ['drop', 'duplicate', 'host', 'count', 'query_order'])
def test_roundtrip_oracle_detects_internal_corruption(mutation):
    source = [query([record('a'), record('b')], selected_count=5), query(host='other')]
    original = payloads._encode_evidence

    def corrupt(queries):
        packet = original(queries)
        refs = packet['queries'][0][3][0][3]
        if mutation == 'drop':
            refs.pop()
        elif mutation == 'duplicate':
            refs.append(refs[0])
        elif mutation == 'host':
            packet['queries'][0][0] = 'changed'
        elif mutation == 'count':
            packet['queries'][0][1] += 1
        else:
            packet['queries'].reverse()
        return packet

    with patch.object(payloads, '_encode_evidence', corrupt), pytest.raises(ValueError):
        payloads.encode_evidence(source)


def test_semantic_oracle_detects_internal_corruption():
    with patch.object(payloads, '_encode_semantic', return_value='lost'), pytest.raises(ValueError):
        payloads.encode_semantic_view(semantic_source())


def test_exact_grouping_may_reorder_without_losing_records():
    source = [query([record('a', 'head'), record('b', 'modifier'), record('c', 'head')])]
    actual = payloads.decode_evidence(payloads.encode_evidence(source))
    assert [r['term'] for r in actual[0]['selected']] == ['a', 'c', 'b']


@pytest.mark.parametrize('source', [None, {}, [None], [{'host': 'incomplete'}]])
def test_unknown_evidence_containers_rejected(source):
    with pytest.raises(ValueError):
        payloads.encode_evidence(source)


def test_lint_both_fields_aliases_case_whitespace_immutability_and_limits():
    source = {'changes': [{'term': 'a', 'reason': 'ROOTED\n IN undefined',
                           'cue': 'ingredient check pending before freeze'}],
              'aliases': [{'term': 'b', 'association_comparison':
                           'Ingredient check pending before freeze'}]}
    frozen = deepcopy(source)
    warnings = payloads.editorial_warnings(source)
    assert [(w['term'], w['rule']) for w in warnings] == [
        ('a', 'undefined_root'), ('b', 'unfinished_ingredient_check')]
    assert source == frozen
    assert payloads.editorial_warnings({'entries': [{'term': 'c',
        'reason': 'Pending culture; target is undefined.',
        'cue': 'rooted in undefined'}]}) == []
    with pytest.raises(ValueError):
        payloads.editorial_warnings({})


class Stdout:
    def __init__(self):
        self.buffer = io.BytesIO()

    def write(self, text):
        raise AssertionError('Must emit UTF-8 bytes, not locale-dependent text')


def test_cli_utf8_bytes_and_immutable_input():
    stdout = Stdout()
    source = semantic_source().encode('utf-8')
    with patch.object(Path, 'read_bytes', return_value=source), patch.object(payloads.sys, 'stdout', stdout):
        assert payloads.main(['semantic', '--input', str(Path(__file__).resolve())]) == 0
    expected = payloads.SEMANTIC_INSTRUCTIONS + payloads.encode_semantic_view(source.decode('utf-8'))
    assert stdout.buffer.getvalue() == expected.encode('utf-8')
    assert b'\xce\xb1' in stdout.buffer.getvalue()


@pytest.mark.parametrize('command,source', [('evidence', '[]'), ('lint', '{"entries":[]}')])
def test_cli_json_and_lint_nonapproval(command, source):
    stdout = Stdout()
    with patch.object(Path, 'read_bytes', return_value=source.encode()), patch.object(payloads.sys, 'stdout', stdout):
        assert payloads.main([command, '--input', str(Path(__file__).resolve())]) == 0
    output = stdout.buffer.getvalue().decode('utf-8')
    if command == 'lint':
        result = json.loads(output)
        assert result['warnings'] == []
        assert result['clinical_approval'] is False
        assert 'quota' in result['limits']
    else:
        assert payloads.decode_evidence(json.loads(output[len(payloads.EVIDENCE_INSTRUCTIONS):])) == []


def test_cli_duplicate_json_keys_rejected():
    stdout = Stdout()
    with patch.object(Path, 'read_bytes', return_value=b'{"entries":[],"entries":[]}'), patch.object(payloads.sys, 'stdout', stdout):
        assert payloads.main(['lint', '--input', str(Path(__file__).resolve())]) == 2
    assert 'Duplicate' in json.loads(stdout.buffer.getvalue())['error']


def test_input_path_rejects_outside_repo():
    with pytest.raises(ValueError):
        payloads._input_path(ROOT.parent)
    assert payloads._input_path('tests/test_chapter_cue_review_payloads.py') == Path(__file__).resolve()


def test_resolved_external_file_is_rejected_before_read():
    original = Path.resolve
    outside = ROOT.parent / 'external-payload.json'

    def resolve(path, *args, **kwargs):
        if path.name == 'escaped-input.json':
            return outside
        return original(path, *args, **kwargs)

    with patch.object(Path, 'resolve', resolve), patch.object(Path, 'read_bytes') as read:
        with pytest.raises(ValueError):
            payloads._input_path('escaped-input.json')
        read.assert_not_called()
