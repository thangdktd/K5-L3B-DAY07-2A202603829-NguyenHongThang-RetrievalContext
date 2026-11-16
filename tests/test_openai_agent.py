import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from openai_agent import OpenAIController,run_openai_agent,pack_agent_context

A='a'*64;B='b'*64

def chunk(cid,text):return dict(id=cid,text=text,source_id='manual',source='manual.pdf',page=32,metadata={},score=1)

def response(name,args,number=1,status='completed'):
    import json
    class Item:
        def model_dump(self,**kwargs):return {'type':'function_call','name':name,'arguments':json.dumps(args),'call_id':f'call{number}'}
    class Usage:
        def model_dump(self):return {'input_tokens':100,'output_tokens':25,'input_tokens_details':{'cached_tokens':10}}
    return SimpleNamespace(output=[Item()],usage=Usage(),model='gpt-4.1-mini-2025-04-14',id=f'resp{number}',status=status)

class Client:
    def __init__(self,responses):self.items=iter(responses);self.requests=[];self.responses=self
    def create(self,**kwargs):
        self.requests.append(kwargs)
        r=next(self.items)
        if isinstance(r,Exception):raise r
        return r

class Retriever:
    def __init__(self,rows):self.rows=iter(rows);self.calls=[]
    def search(self,query,top_k):self.calls.append((query,top_k));return next(self.rows)

class OpenAIAgentTests(unittest.TestCase):
    def test_real_function_protocol_and_complete_comparison(self):
        api=Client([response('search',{'query':'Compare modes'}),response('search',{'query':'Mode 2 purpose'},2),
                    response('finish',{'status':'answered','answer':f'Mode 1 monitors [{A}]. Mode 2 changes [{B}].','citations':[A,B]},3)])
        controller=OpenAIController(api)
        result=run_openai_agent('Compare modes',controller,Retriever([[chunk(A,'Mode 1 monitors')],[chunk(B,'Mode 2 changes'),chunk(A,'Mode 1 monitors')]]))
        self.assertEqual(result['status'],'answered')
        self.assertEqual(set(result['context_ids']),{A,B})
        self.assertEqual(len(result['context_ids']),2)
        self.assertEqual(result['usage'],{'input_tokens':300,'output_tokens':75,'cached_input_tokens':30})
        self.assertEqual(api.requests[0]['tool_choice'],{'type':'function','name':'search'})
        self.assertFalse(api.requests[0]['store'])
        last=api.requests[-1]['input']
        self.assertEqual(last[1]['call_id'],last[2]['call_id'])
        self.assertEqual(last[2]['type'],'function_call_output')
        self.assertNotIn('gold',str(api.requests));self.assertNotIn('expected_answer',str(api.requests))
        self.assertIn('source_id=manual',result['context'])

    def test_missing_comparison_side_can_abstain(self):
        api=Client([response('search',{'query':'Compare modes'}),response('finish',{'status':'abstain','answer':'Missing Mode 2 evidence','citations':[]},2)])
        result=run_openai_agent('Compare modes',OpenAIController(api),Retriever([[chunk(A,'Mode 1 monitors')]]))
        self.assertEqual(result['status'],'abstain')
        self.assertEqual(result['citations'],[])

    def test_unknown_citation_and_unlisted_inline_id_rejected(self):
        for cited,answer in [([B],f'Answer [{B}]'),([A],f'Answer [{A}] invented [{B}]')]:
            api=Client([response('search',{'query':'q'}),response('finish',{'status':'answered','answer':answer,'citations':cited},2)])
            result=run_openai_agent('q',OpenAIController(api),Retriever([[chunk(A,'fact')]]))
            self.assertEqual(result['reason'],'invalid_or_missing_citations')

    def test_max_three_searches_then_forced_finish(self):
        api=Client([response('search',{'query':str(i)},i) for i in range(3)]+[response('finish',{'status':'abstain','answer':'Missing','citations':[]},4)])
        retriever=Retriever([[],[],[]]);result=run_openai_agent('q',OpenAIController(api),retriever)
        self.assertEqual(len(retriever.calls),3)
        self.assertEqual(api.requests[-1]['tool_choice'],{'type':'function','name':'finish'})
        self.assertEqual([t['name'] for t in api.requests[-1]['tools']],['finish'])
        self.assertEqual(result['status'],'abstain')

    def test_context_budget_and_latest_evidence_replaces_old(self):
        old,new=chunk(A,'old'*20),chunk(B,'new'*20)
        context,ids=pack_agent_context([new,old,new],budget=180)
        self.assertLessEqual(len(context),180)
        self.assertEqual(ids,[B])
        self.assertNotIn('old',context)

    def test_provider_error_is_sanitized_and_not_abstention(self):
        api=Client([RuntimeError('SECRET_MUST_NOT_APPEAR')]);result=run_openai_agent('q',OpenAIController(api),Retriever([]))
        self.assertEqual(result['status'],'error');self.assertFalse(result['abstention'])
        self.assertEqual(result['reason'],'provider_error')
        self.assertNotIn('SECRET_MUST_NOT_APPEAR',str(result))

    def test_retrieval_error_is_not_abstention(self):
        class Broken:
            def search(self,*args,**kwargs):raise ConnectionError('SECRET_MUST_NOT_APPEAR')
        api=Client([response('search',{'query':'q'})]);r=run_openai_agent('q',OpenAIController(api),Broken())
        self.assertEqual(r['status'],'error');self.assertEqual(r['reason'],'retrieval_error')
        self.assertNotIn('SECRET_MUST_NOT_APPEAR',str(r))

    def test_invalid_arguments_and_incomplete_response_are_errors(self):
        for r in [response('search',{'query':''}),response('unknown',{}),response('search',{'query':'q'},status='incomplete')]:
            result=run_openai_agent('q',OpenAIController(Client([r])),Retriever([]))
            self.assertEqual(result['reason'],'model_protocol_error')

    def test_client_uses_official_endpoint_and_no_key_logging(self):
        from run_agent_dev import make_client
        with patch.dict('os.environ',{'OPENAI_API_KEY':'unit-test-placeholder'}),patch('openai.OpenAI') as sdk:
            make_client()
            self.assertEqual(sdk.call_args.kwargs['base_url'],'https://api.openai.com/v1')
            self.assertEqual(sdk.call_args.kwargs['max_retries'],0)

if __name__=='__main__':unittest.main()
