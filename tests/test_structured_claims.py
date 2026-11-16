"""Structured per-claim citation tests; all model calls mocked."""
import json
import sys
import unittest
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).resolve().parent)]
from openai_agent import OpenAIController,run_openai_agent,render_supported_claims,FINISH
from test_openai_agent import Client,Retriever,response,chunk,A,B

class StructuredClaimTests(unittest.TestCase):
    def run_claims(self,claims,rows=None,status='answered'):
        api=Client([response('search',{'query':'Compare modes'}),response('finish',{'status':status,'claims':claims},2)])
        r=run_openai_agent('Compare modes',OpenAIController(api),Retriever([rows if rows is not None else [chunk(A,'Mode 1 monitors.'),chunk(B,'Mode 2 changes.')]]))
        self.assertEqual(len(api.requests),2)
        return r

    def test_two_claims_two_chunks_render_only_selected_sources(self):
        claims=[{'text':'Mode 1 monitors.','chunk_ids':[A]},{'text':'Mode 2 changes.','chunk_ids':[B]}]
        r=self.run_claims(claims)
        self.assertEqual(r['status'],'answered')
        self.assertEqual(r['answer'],f'Mode 1 monitors. [{A}]\nMode 2 changes. [{B}]')
        self.assertEqual(r['citations'],[A,B])
        self.assertEqual(r['events'][-1]['claims'],claims)

    def test_missing_one_required_source_rejects_entire_answer(self):
        claims=[{'text':'Mode 1 monitors.','chunk_ids':[A]},{'text':'Mode 2 changes.','chunk_ids':[B]}]
        r=self.run_claims(claims,rows=[chunk(A,'Mode 1 monitors.')])
        self.assertEqual(r['status'],'abstain')
        self.assertEqual(r['citations'],[])
        self.assertNotIn('Mode 1',r['answer'])

    def test_claim_with_no_source_is_not_filled_by_renderer(self):
        r=self.run_claims([{'text':'Mode 1 monitors.','chunk_ids':[A]},{'text':'Mode 2 changes.','chunk_ids':[]}])
        self.assertEqual(r['reason'],'missing_claim_evidence')
        self.assertEqual(r['status'],'abstain')

    def test_valid_id_without_support_and_swapped_sources_fail(self):
        for claims in [[{'text':'Invented pressure 999.','chunk_ids':[A]}],
                       [{'text':'Mode 1 monitors.','chunk_ids':[B]},{'text':'Mode 2 changes.','chunk_ids':[A]}]]:
            r=self.run_claims(claims)
            self.assertEqual(r['status'],'abstain')
            self.assertEqual(r['reason'],'unsupported_cited_claim')

    def test_unknown_malformed_or_extra_source_not_accepted(self):
        for ids in [['z'*64],['short'],['c'*64],[A,B]]:
            r=self.run_claims([{'text':'Mode 1 monitors.','chunk_ids':ids}])
            self.assertEqual(r['status'],'abstain')

    def test_multiple_claims_same_source_deduplicates_array(self):
        r=self.run_claims([{'text':'Mode 1 monitors.','chunk_ids':[A]},{'text':'Mode 2 changes.','chunk_ids':[A]}],
                          rows=[chunk(A,'Mode 1 monitors. Mode 2 changes.')])
        self.assertEqual(r['status'],'answered')
        self.assertEqual(r['citations'],[A])
        self.assertEqual(r['answer'].count(f'[{A}]'),2)

    def test_explicit_abstention_never_promoted(self):
        for claims in [[],[{'text':'Mode 1 monitors.','chunk_ids':[A]}]]:
            r=self.run_claims(claims,status='abstain')
            self.assertEqual(r['status'],'abstain');self.assertEqual(r['citations'],[])
            self.assertEqual(r['reason'],'model_abstention')

    def test_empty_and_malformed_claims_fail_closed(self):
        for claims in [[],[{'text':'Mode 1 monitors.'}],[{'text':'','chunk_ids':[A]}],
                       [{'text':'Mode 1 monitors.','chunk_ids':[A],'extra':'ignored?'}],
                       [{'text':'Mode 1 monitors.','chunk_ids':[None]}]]:
            self.assertEqual(self.run_claims(claims)['status'],'abstain')

    def test_schema_is_per_claim_and_old_finish_is_not_advertised(self):
        schema=FINISH['parameters']
        self.assertEqual(set(schema['properties']),{'status','claims'})
        item=schema['properties']['claims']['items']
        self.assertEqual(set(item['required']),{'text','chunk_ids'})
        self.assertFalse(item['additionalProperties'])
        self.assertEqual(item['properties']['chunk_ids']['minItems'],1)
        self.assertTrue(FINISH['strict'])

    def test_supported_multi_source_claim_keeps_each_model_selected_id(self):
        r=self.run_claims([{'text':'Shared instruction.','chunk_ids':[B,A]}],
                          rows=[chunk(A,'Shared instruction.'),chunk(B,'Shared instruction.')])
        self.assertEqual(r['status'],'answered');self.assertEqual(r['citations'],[B,A])
        self.assertEqual(r['answer'],f'Shared instruction. [{B}][{A}]')

if __name__=='__main__':unittest.main()
