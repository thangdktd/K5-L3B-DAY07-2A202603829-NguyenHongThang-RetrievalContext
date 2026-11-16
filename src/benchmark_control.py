"""Validation, deterministic rebuild and freeze controls. No retrieval is run here."""
import argparse
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'starter'))
from baseline import validate, evidence_groups, hit, normalize_text

SCHEMA = 'day07-evidence-groups-v2'
RULES = {
    'groups': 'AND across required gold_groups; OR across alternatives within a group; legacy gold is one OR group',
    'matching': 'source_id AND physical page AND contiguous NFC/whitespace-normalized evidence in a single chunk',
    'hit1': 'all required groups covered by rank 1 alone; strict completeness, including multi-chunk questions',
    'hit3': 'all required groups covered by the union of top 3 chunks',
    'context': 'all required groups covered by packed chunks; full chunks only, source headers included in character budget',
    'denominator': 'answerable questions only; report single-group and multi-group subsets separately',
    'unanswerable': 'full-corpus term inventory plus review of related chunks; keyword absence is not proof of semantic absence',
}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def encoded(value):
    return json.dumps(value, ensure_ascii=False, indent=2).encode('utf-8')

def absence_audit(chunks, cases):
    patterns = {
        'q_unans_dev_01': ['R32', 'retrofit', 'R410A'],
        'q_unans_dev_02': ['sound pressure', 'sound power', 'dBA', 'decibel', 'noise', 'sound'],
        'q_unans_test_01': ['oil', 'viscosity', 'Daphne', 'FVC68', 'lubricant'],
        'q_unans_test_02': ['IGBT', 'switching frequency', 'A1P', 'inverter', 'semiconductor'],
    }
    import re
    rows = []
    for case in cases:
        if case['answerable']:
            continue
        inventory = {}
        ids = set()
        for term in patterns[case['id']]:
            found = [c for c in chunks if re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', normalize_text(c['text']), re.I)]
            inventory[term] = [c['id'] for c in found]
            ids.update(c['id'] for c in found)
        rows.append({'case_id': case['id'], 'split': case['split'], 'terms': inventory,
                     'related_chunks': [{'id': c['id'], 'source_id': c['source_id'], 'page': c['page'], 'text': c['text']} for c in chunks if c['id'] in ids],
                     'review_conclusion': case['absence_reason'],
                     'review_scope': 'Related extracted chunks reviewed; no complete answer identified. No external manuals inspected; extraction may omit visual information.'})
    return {'method': RULES['unanswerable'], 'corpus_chunks_scanned': len(chunks), 'cases': rows}

def validate_all(chunks, questions, cases):
    validate(chunks, questions)
    if len(chunks) != 292 or len(questions) != 20 or len(cases) != 24:
        raise ValueError('Expected 292 chunks, 20 answerable questions, 24 cases')
    if len({c['id'] for c in cases}) != 24:
        raise ValueError('Duplicate case IDs')
    if Counter((c['split'], c['answerable']) for c in cases) != Counter({('dev', True): 15, ('dev', False): 2, ('test', True): 5, ('test', False): 2}):
        raise ValueError('Split membership mismatch')
    lookup = {c['id']: c for c in cases}
    for q in questions:
        c = lookup[q['id']]
        if (q['question'], q['split'], True) != (c['question'], c['split'], c['answerable']):
            raise ValueError('Question/case mismatch')
    for case in cases:
        if type(case['answerable']) is not bool or case['split'] not in ('dev', 'test'):
            raise ValueError('Invalid case schema')
        if not case['answerable'] and (not case.get('absence_reason') or case.get('expected_behavior') != 'search_and_abstain'):
            raise ValueError('Missing absence annotation')
    for c in chunks:
        m = c['metadata']
        if type(c['page']) is not int or c['page'] < 1 or (m['page'], m['source_id'], m['strategy']) != (c['page'], c['source_id'], 'B'):
            raise ValueError('Chunk provenance mismatch')
        if hashlib.sha256(c['text'].encode()).hexdigest() != m['text_sha256']:
            raise ValueError('Chunk content hash mismatch')
    return {'chunks': 292, 'questions': 20, 'cases': 24, 'dev_answerable': 15, 'dev_unanswerable': 2,
            'test_answerable': 5, 'test_unanswerable': 2,
            'evidence_resolution': {q['id']: [[c['id'] for c in chunks if hit(c, g)] for g in evidence_groups(q)] for q in questions}}

def verify_frozen(root=ROOT):
    manifest = json.loads((root / 'data/benchmark_manifest.json').read_text(encoding='utf-8'))
    for name, info in manifest['files'].items():
        if digest(root / name) != info['sha256']:
            raise ValueError('Frozen file changed: ' + name)
    return manifest

def run_builder(build):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Rebuild in memory and compare bytes; never write')
    parser.add_argument('--freeze', action='store_true')
    args = parser.parse_args()
    manifest_path = ROOT / 'data/benchmark_manifest.json'
    if manifest_path.exists() and not args.check:
        raise SystemExit('Benchmark frozen: only --check is permitted')
    chunks = json.loads((ROOT / 'data/chunks.json').read_text(encoding='utf-8'))
    questions, cases = build()
    validation = validate_all(chunks, questions, cases)
    audit = absence_audit(chunks, cases)
    outputs = {'data/questions.json': questions, 'data/agent_cases.json': cases,
               'data/benchmark_validation.json': validation, 'data/unanswerable_audit.json': audit}
    if args.check:
        for name, value in outputs.items():
            if (ROOT / name).read_bytes() != encoded(value):
                raise ValueError('Rebuild differs: ' + name)
        if manifest_path.exists():
            verify_frozen()
        print('Deterministic rebuild and frozen hashes: PASS; TEST retrieval queries: 0')
        return
    for name, value in outputs.items():
        (ROOT / name).write_bytes(encoded(value))
    if args.freeze:
        names = list(outputs) + ['data/chunks.json', 'data/questions_day6_raw.json',
                  'src/build_final_benchmark.py', 'src/benchmark_control.py', 'starter/baseline.py', 'data/README.md']
        files = {name: {'sha256': digest(ROOT / name)} for name in names}
        for name in outputs:
            if isinstance(outputs[name], list):
                files[name]['records'] = len(outputs[name])
        files['data/chunks.json']['records'] = len(chunks)
        files['data/questions_day6_raw.json']['records'] = len(json.loads((ROOT/'data/questions_day6_raw.json').read_text(encoding='utf-8')))
        manifest = {'schema_version': SCHEMA, 'frozen_at': datetime.now(ZoneInfo('Asia/Bangkok')).isoformat(),
                    'timezone': 'Asia/Bangkok', 'counts': {k:v for k,v in validation.items() if k != 'evidence_resolution'},
                    'scoring': RULES, 'files': files, 'official_basis': ['BENCHMARK.md sections 1-2', 'data/README.md'],
                    'test_retrieval_queries_run': 0, 'reproduce': '.venv/Scripts/python.exe -X utf8 src/build_final_benchmark.py --check'}
        manifest_path.write_bytes(encoded(manifest))
    print('Benchmark validation PASS; freeze=' + str(args.freeze) + '; TEST retrieval queries: 0')
