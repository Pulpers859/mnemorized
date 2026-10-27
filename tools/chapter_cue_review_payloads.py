"""Lossless local review representations and warning-only editorial checks.

Promotes the audited round4 semantic table and round5 evidence/lint algorithms.
These representations establish neither clinical admission nor quota savings.
"""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sys


SEMANTIC_INSTRUCTIONS = (
    'Semantic rows use ordered columns in the $semantic_columns header. '
    'Every following JSON array supplies all column values, including nulls. '
    '$semantic_end ends the table. Other text is unchanged. '
    'Review every row and all notes; no field or qualification is omitted.\n'
)
EVIDENCE_INSTRUCTIONS = (
    'Queries and cards use the named ordered columns. Each ref CHAPTER#ID expands '
    'to docs/chapter-CHAPTER-cue-audit.json#ID; its term is ID unless ref is a '
    '[shortRef,term] pair. Status and scope are exact, not interchangeable terms. '
    'Matched counts are corpus totals; shown counts are the numbers of refs. '
    'Shown below matched means truncated; forms are bounded, not exhaustive. '
    'Keep selected and held separate. No hit is not proof of novelty.\n'
)
HEADER = '{"$semantic_columns":'
END = '{"$semantic_end":true}'
QUERY_COLUMNS = ['host', 'matched_selected', 'matched_held', 'selected', 'held']
CARD_COLUMNS = ['cue', 'cue_scope', 'status', 'refs']
PREFIX = 'docs/chapter-'
SUFFIX = '-cue-audit.json'
LIMITS = (
    'Warning-only: a clean result means only that the two configured phrases '
    'were not detected. Not schema validation, clinical correctness, clinical '
    'cue approval, exhaustive editorial coverage, comprehension equivalence, '
    'or measured token/cost/quota savings.'
)
RULES = {
    'undefined_root': re.compile(r'\brooted\s+in\s+undefined\b', re.I),
    'unfinished_ingredient_check': re.compile(
        r'\bingredient\s+check\s+pending\s+before\s+freeze\b', re.I),
}


def _unique_object(pairs):
    if len({key for key, _ in pairs}) != len(pairs):
        raise ValueError('Duplicate JSON object key')
    return dict(pairs)


def _reject_constant(value):
    raise ValueError('Non-JSON numeric constant: ' + value)


def _loads(text):
    return json.loads(text, object_pairs_hook=_unique_object,
                      parse_constant=_reject_constant)


def _encode_semantic(text):
    if HEADER in text or END in text:
        raise ValueError('Reserved marker in source')
    first = text.find('{"row": ')
    if first < 0:
        return text
    prefix, lines = text[:first], text[first:].splitlines(keepends=True)
    columns, rows, index = None, [], 0
    for line in lines:
        if not line.startswith('{"row": '):
            break
        obj = _loads(line)
        if columns is None:
            columns = list(obj)
        if list(obj) != columns or json.dumps(obj, ensure_ascii=True) + '\n' != line:
            raise ValueError('Unsupported row layout; use original view')
        rows.append(json.dumps(list(obj.values()), ensure_ascii=False,
                               separators=(',', ':')) + '\n')
        index += 1
    return (prefix + HEADER + json.dumps(columns, separators=(',', ':')) + '}\n'
            + ''.join(rows) + END + '\n' + ''.join(lines[index:]))


def decode_semantic_view(text):
    """Expand the audited table; retain all surrounding text verbatim."""
    first = text.find(HEADER)
    if first < 0:
        return text
    prefix, lines = text[:first], text[first:].splitlines(keepends=True)
    obj = _loads(lines[0])
    if not isinstance(obj, dict) or set(obj) != {'$semantic_columns'}:
        raise ValueError('Invalid header')
    columns = obj['$semantic_columns']
    if (not isinstance(columns, list) or not columns
            or not all(isinstance(x, str) for x in columns)
            or len(set(columns)) != len(columns)):
        raise ValueError('Invalid columns')
    rows = []
    for index, line in enumerate(lines[1:], 1):
        if line.rstrip('\n') == END:
            return prefix + ''.join(rows) + ''.join(lines[index + 1:])
        values = _loads(line)
        if not isinstance(values, list) or len(values) != len(columns):
            raise ValueError('Invalid row width')
        rows.append(json.dumps(dict(zip(columns, values)), ensure_ascii=True) + '\n')
    raise ValueError('Missing end marker')


def encode_semantic_view(text):
    """Encode only supported row layouts, with exact text reconstruction."""
    if not isinstance(text, str):
        raise ValueError('Expected text')
    packet = _encode_semantic(text)
    if decode_semantic_view(packet) != text:
        raise ValueError('Semantic roundtrip mismatch')
    return packet


def _short_ref(ref, term):
    path, sep, identifier = ref.partition('#')
    if not sep or not path.startswith(PREFIX) or not path.endswith(SUFFIX):
        raise ValueError('Unexpected reference syntax')
    chapter = path[len(PREFIX):-len(SUFFIX)]
    if (not re.fullmatch(r'[1-9][0-9]*[A-Z]?', chapter)
            or not identifier.strip() or not isinstance(term, str) or not term.strip()):
        raise ValueError('Invalid chapter/identifier/term')
    short = chapter + '#' + identifier
    return short if identifier == term else [short, term]


def _full_ref(value):
    if isinstance(value, str):
        short = value
        term = value.partition('#')[2]
    elif isinstance(value, list) and len(value) == 2 and all(isinstance(x, str) for x in value):
        short, term = value
    else:
        raise ValueError('Invalid reference')
    chapter, sep, identifier = short.partition('#')
    if (not sep or not re.fullmatch(r'[1-9][0-9]*[A-Z]?', chapter)
            or not identifier.strip() or not term.strip()):
        raise ValueError('Invalid reference')
    return PREFIX + chapter + SUFFIX + '#' + identifier, term


def _fields(value, fields):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError('Unexpected fields/schema')


def _list(value):
    if not isinstance(value, list):
        raise ValueError('Expected list')
    return value


def _encode_evidence(queries):
    output = []
    for query in _list(queries):
        _fields(query, ('host', 'selected_forms', 'held_forms', 'selected_count', 'held_count'))
        row = [query['host'], query['selected_count'], query['held_count']]
        for label in ('selected', 'held'):
            groups = defaultdict(list)
            for form in _list(query[label + '_forms']):
                _fields(form, ('cue', 'records'))
                if not isinstance(form['cue'], str):
                    raise ValueError('Invalid cue')
                form_records = _list(form['records'])
                if not form_records:
                    raise ValueError('Empty evidence form cannot be represented; use original view')
                for record in form_records:
                    _fields(record, ('ref', 'term', 'status', 'cue_scope'))
                    if (not isinstance(record['ref'], str)
                            or not isinstance(record['status'], str)
                            or not (record['cue_scope'] is None
                                    or isinstance(record['cue_scope'], str))):
                        raise ValueError('Invalid record')
                    groups[(form['cue'], record['cue_scope'], record['status'])].append(
                        _short_ref(record['ref'], record['term']))
            row.append([[cue, scope, status, refs]
                        for (cue, scope, status), refs in groups.items()])
        output.append(row)
    return {'query_columns': QUERY_COLUMNS.copy(), 'card_columns': CARD_COLUMNS.copy(),
            'queries': output}


def decode_evidence(packet):
    """Expand cards without deduplication or membership/scope inference."""
    _fields(packet, ('query_columns', 'card_columns', 'queries'))
    if packet['query_columns'] != QUERY_COLUMNS or packet['card_columns'] != CARD_COLUMNS:
        raise ValueError('Invalid schema')
    queries = []
    for row in _list(packet['queries']):
        if not isinstance(row, list) or len(row) != 5 or not isinstance(row[0], str):
            raise ValueError('Invalid query row')
        if any(type(count) is not int or count < 0 for count in row[1:3]):
            raise ValueError('Invalid counts')
        query = {'host': row[0], 'selected_count': row[1], 'held_count': row[2]}
        for label, cards in zip(('selected', 'held'), row[3:]):
            records = []
            for card in _list(cards):
                if not isinstance(card, list) or len(card) != 4:
                    raise ValueError('Invalid card')
                cue, scope, status, refs = card
                if (not isinstance(cue, str) or not (scope is None or isinstance(scope, str))
                        or not isinstance(refs, list) or not refs):
                    raise ValueError('Invalid evidence')
                if (not isinstance(status, str)
                        or status not in ({'hold'} if label == 'held'
                                          else {'retain_candidate', 'reuse_candidate'})):
                    raise ValueError('Status does not match membership')
                for ref in refs:
                    full, term = _full_ref(ref)
                    records.append({'ref': full, 'term': term, 'status': status,
                                    'cue': cue, 'cue_scope': scope})
            if len(records) > query[label + '_count']:
                raise ValueError('Displayed records exceed total')
            query[label] = records
        queries.append(query)
    return queries


def _multiset(records):
    return Counter(json.dumps(row, sort_keys=True, ensure_ascii=True, allow_nan=False)
                   for row in records)


def encode_evidence(queries):
    """Verify ordered query identities/counts and exact per-membership multisets."""
    packet = _encode_evidence(queries)
    decoded = decode_evidence(packet)
    if len(queries) != len(decoded):
        raise ValueError('Query count mismatch')
    for source, actual in zip(queries, decoded):
        if any(source[key] != actual[key]
               for key in ('host', 'selected_count', 'held_count')):
            raise ValueError('Query identity/count mismatch')
        for label in ('selected', 'held'):
            expected = [dict(record, cue=form['cue'])
                        for form in source[label + '_forms'] for record in form['records']]
            if _multiset(expected) != _multiset(actual[label]):
                raise ValueError('Evidence record multiset mismatch')
    return packet


def editorial_warnings(document):
    """Two warning rules only; unrelated bank metadata is not schema-validated."""
    if not isinstance(document, dict):
        raise ValueError('Expected chapter bank or sparse decisions')
    if 'entries' in document and 'changes' not in document:
        rows = _list(document['entries'])
    elif 'changes' in document and 'entries' not in document:
        rows = _list(document['changes']) + _list(document.get('aliases', []))
    else:
        raise ValueError('Expected chapter bank or sparse decisions')
    output = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('term'), str):
            raise ValueError('Invalid editorial row')
        for field in ('reason', 'association_comparison'):
            note = row.get(field)
            if not isinstance(note, str):
                continue
            for name, pattern in RULES.items():
                if pattern.search(note):
                    output.append({'term': row['term'], 'field': field,
                                   'rule': name, 'note': note})
    return output


def _input_path(value):
    root = Path(__file__).resolve().parents[1]
    path = Path(value)
    path = (root / path).resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError('Input must resolve to a file inside the repository')
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest='command', required=True)
    for name in ('semantic', 'evidence', 'lint'):
        subcommands.add_parser(name).add_argument('--input', required=True)
    args = parser.parse_args(argv)
    try:
        # Decode bytes explicitly: newline translation would invalidate text fidelity.
        source = _input_path(args.input).read_bytes().decode('utf-8')
        if args.command == 'semantic':
            output = SEMANTIC_INSTRUCTIONS + encode_semantic_view(source)
        elif args.command == 'evidence':
            output = EVIDENCE_INSTRUCTIONS + json.dumps(
                encode_evidence(_loads(source)), ensure_ascii=True, separators=(',', ':')) + '\n'
        else:
            output = json.dumps({'warnings': editorial_warnings(_loads(source)),
                                 'clinical_approval': False, 'limits': LIMITS},
                                ensure_ascii=False) + '\n'
    except (ValueError, OSError) as error:
        sys.stdout.buffer.write((json.dumps({'error': str(error)}, ensure_ascii=False)
                                 + '\n').encode('utf-8'))
        return 2
    sys.stdout.buffer.write(output.encode('utf-8'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
