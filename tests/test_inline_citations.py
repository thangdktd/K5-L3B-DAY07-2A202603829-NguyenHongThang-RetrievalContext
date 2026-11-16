"""Citation acceptance tests with mocked model output; no external requests."""
import sys
from pathlib import Path
import unittest
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).resolve().parent)]
from openai_agent import OpenAIController,run_openai_agent,validate_cited_answer
from test_openai_agent import Client,Retriever,response,chunk,A,B

class InlineCitationTests(unittest.TestCase):
    def run_case(self,answer,citations,rows=None,status='answered'):
        api=Client([response('search',{'query':'Compare purposes'}),
                    response('finish',{'status':status,'answer':answer,'citations':citations},2)])
        r=run_openai_agent('Compare purposes',OpenAIController(api),Retriever([rows or [chunk(A,'Mode 1 monitors.'),chunk(B,'Mode 2 changes.')]]))
        self.assertEqual(len(api.requests),2)
        return r

    def test_inline_supported_claim_passes(self):
        r=self.run_case(f'Mode 1 monitors [{A}]',[A])
        self.assertEqual(r['status'],'answered')
        self.assertEqual(r['citations'],[A])
        self.assertEqual(r['answer'],f'Mode 1 monitors [{A}]')

    def test_array_without_inline_fails_and_no_citation_is_inserted(self):
        r=self.run_case('Mode 1 monitors.',[A])
        self.assertEqual(r['status'],'abstain')
        self.assertEqual(r['reason'],'invalid_or_missing_citations')
        self.assertEqual(r['citations'],[])
        self.assertNotIn(A,r['answer'])
        self.assertEqual(r['events'][-1]['proposed_answer'],'Mode 1 monitors.')

    def test_citation_outside_current_context_fails(self):
        r=self.run_case(f'Mode 1 monitors [{B}]',[B],rows=[chunk(A,'Mode 1 monitors.')])
        self.assertEqual(r['status'],'abstain')

    def test_malformed_citations_fail(self):
        for rendered,citations in [(f'[ {A} ]',[A]),(f'({A})',[A]),('[chunk-id]',['chunk-id']),
                                   (f'[{A.upper()}]',[A.upper()]),(f'[[{A}]]',[A])]:
            with self.subTest(rendered=rendered):
                self.assertEqual(self.run_case('Mode 1 monitors '+rendered,citations)['status'],'abstain')

    def test_multiple_claims_require_correct_adjacent_support(self):
        answer=f'Mode 1 monitors [{A}].\nMode 2 changes [{B}].'
        r=self.run_case(answer,[A,B])
        self.assertEqual(r['status'],'answered')
        self.assertEqual(r['citations'],[A,B])
        for bad in [f'Mode 1 monitors [{B}]. Mode 2 changes [{A}].',
                    f'Mode 1 monitors [{A}]. Mode 2 changes.',
                    f'Mode 1 monitors [{A}]. Imaginary fact [{B}].']:
            self.assertEqual(self.run_case(bad,[A,B])['status'],'abstain')

    def test_abstention_is_never_promoted_by_citations(self):
        r=self.run_case(f'Insufficient evidence [{A}]',[A],status='abstain')
        self.assertEqual(r['status'],'abstain')
        self.assertEqual(r['reason'],'model_abstention')
        self.assertEqual(r['citations'],[])
        self.assertNotIn(A,r['answer'])

    def test_existing_but_irrelevant_citation_fails(self):
        r=self.run_case(f'Mode 1 monitors [{B}]',[B])
        self.assertEqual(r['status'],'abstain')
        self.assertEqual(r['reason'],'unsupported_cited_claim')

    def test_numeric_substring_does_not_establish_support(self):
        self.assertFalse(validate_cited_answer(f'6 hours [{A}]',[A],[chunk(A,'36 hours before operation')])[0])
        self.assertTrue(validate_cited_answer(f'6 hours [{A}]',[A],[chunk(A,'6 hours')])[0])
        self.assertFalse(validate_cited_answer(f'6 hours [{A}]',[A],[chunk(A,'-6 hours before operation')])[0])

    def test_unused_array_citation_and_unlisted_inline_citation_fail(self):
        self.assertEqual(self.run_case(f'Mode 1 monitors [{A}]',[A,B])['status'],'abstain')
        self.assertEqual(self.run_case(f'Mode 1 monitors [{A}]. Mode 2 changes [{B}].',[A])['status'],'abstain')

if __name__=='__main__':unittest.main()
