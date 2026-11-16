import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'starter'))
from baseline import evidence_complete, evaluate, validate

def chunk(cid, text, source='doc', page=32):
    return dict(id=cid, text=text, source_id=source, source='manual.pdf', page=page, metadata={})

def gold(text, source='doc', page=32):
    return dict(source_id=source, page=page, evidence=text)

class GroupEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.a = chunk('a', 'Mode 1 monitors.')
        self.b = chunk('b', 'Mode 2 changes.')
        self.q = dict(id='q', split='dev', question='Compare modes', expected_answer='Both modes',
                      gold_groups=[[gold('Mode 1 monitors.')], [gold('Mode 2 changes.')]])

    def test_only_mode1_fails(self):
        self.assertFalse(evidence_complete([self.a], self.q))

    def test_only_mode2_fails(self):
        self.assertFalse(evidence_complete([self.b], self.q))

    def test_both_in_one_chunk_passes(self):
        self.assertTrue(evidence_complete([chunk('c', self.a['text']+' '+self.b['text'])], self.q))

    def test_distinct_chunks_pass_top3_and_context_but_not_top1(self):
        class Index:
            def search(inner, question, top_k): return [self.a, self.b]
        validate([self.a, self.b], [self.q])
        trace = evaluate(Index(), [self.q], budget=800)[0]
        self.assertFalse(trace['hit1'])
        self.assertTrue(trace['hit3'])
        self.assertTrue(trace['context_hit'])
        trace = evaluate(Index(), [self.q], budget=55)[0]
        self.assertFalse(trace['context_hit'])

    def test_alternatives_are_or(self):
        q = {**self.q, 'gold_groups': [[gold('alternative'), gold(self.a['text'])], [gold(self.b['text'])]]}
        self.assertTrue(evidence_complete([self.a, self.b], q))

    def test_wrong_source_or_page_fails(self):
        for bad in [chunk('b', self.b['text'], source='other'), chunk('b', self.b['text'], page=33)]:
            self.assertFalse(evidence_complete([self.a, bad], self.q))

    def test_legacy_gold_and_empty_groups(self):
        q = {k:v for k,v in self.q.items() if k != 'gold_groups'}
        q['gold'] = [gold('alternative'), gold(self.a['text'])]
        self.assertTrue(evidence_complete([self.a], q))
        for groups in [[], [[]], None]:
            with self.assertRaises(ValueError): evidence_complete([self.a], {**self.q, 'gold_groups': groups})
        with self.assertRaises(ValueError): evidence_complete([self.a], {**self.q, 'gold': q['gold']})

if __name__ == '__main__': unittest.main()
