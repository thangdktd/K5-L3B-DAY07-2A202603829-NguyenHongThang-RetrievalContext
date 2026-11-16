"""Offline SDK transport tests: no API, Agent or retrieval execution."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import diagnose_openai as diagnostic
from openai import OpenAI,DefaultHttpxClient
import httpx2

class DiagnosticTests(unittest.TestCase):
    def run_mock(self,handler):
        requests=[]
        def transport(request):
            requests.append(request)
            return handler(request)
        def factory(**kwargs):
            kwargs['http_client'].close()
            # Preserve diagnostic HTTP hooks while replacing sockets with mocks.
            kwargs['http_client']=DefaultHttpxClient(timeout=20,max_redirects=0,follow_redirects=False,
                event_hooks=hooks[0],transport=httpx2.MockTransport(transport))
            return OpenAI(**kwargs)
        hooks=[]
        from openai import DefaultHttpxClient as RealHttpClient
        def http_factory(**kwargs):
            hooks.append(kwargs['event_hooks']);return RealHttpClient(**kwargs)
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'result.json'
            with patch.dict('os.environ',{'OPENAI_API_KEY':'unit-private-secret'}),\
                 patch('dotenv.load_dotenv'),patch('openai.OpenAI',side_effect=factory),\
                 patch('openai.DefaultHttpxClient',side_effect=http_factory),\
                 patch.object(sys,'argv',['diagnose_openai','--output',str(output)]),\
                 contextlib.redirect_stdout(io.StringIO()) as stdout:
                diagnostic.main()
            report=json.loads(output.read_text(encoding='utf-8'))
            self.assertNotIn('unit-private-secret',output.read_text(encoding='utf-8')+stdout.getvalue())
        return report,requests

    def test_http400_safe_structured_fields_and_responses_payload(self):
        def handler(request):
            return httpx2.Response(400,json={'error':{
                'code':'invalid_value','type':'invalid_request_error','param':'max_output_tokens',
                'message':"Invalid 'max_output_tokens': minimum 16. Authorization: Bearer unit-private-secret; PRIVATE-PROMPT",
                'sensitive_extra':'DO-NOT-LOG'}})
        report,requests=self.run_mock(handler)
        self.assertEqual(len(requests),1)
        self.assertEqual(report['status_code'],400)
        self.assertEqual(report['error']['code'],'invalid_value')
        self.assertEqual(report['error']['type'],'invalid_request_error')
        self.assertEqual(report['error']['param'],'max_output_tokens')
        self.assertIn('Minimum allowed: 16',report['error']['message'])
        for private in ('PRIVATE-PROMPT','DO-NOT-LOG','Authorization','Bearer'):
            self.assertNotIn(private,json.dumps(report))
        self.assertEqual(requests[0].url.path,'/v1/responses')
        body=json.loads(requests[0].content)
        self.assertEqual(body,{'model':'gpt-4.1-mini','input':'Reply OK','max_output_tokens':16,'store':False})
        self.assertEqual(report['timeout_seconds'],20)
        self.assertEqual(report['max_retries'],0)

    def test_timeout_no_retry_or_sensitive_exception_text(self):
        def handler(request):raise httpx2.ReadTimeout('PRIVATE-TIMEOUT unit-private-secret',request=request)
        report,requests=self.run_mock(handler)
        self.assertEqual(len(requests),1)
        self.assertEqual(report['request_attempts'],1)
        self.assertIn('APITimeoutError',report['exception_types'])
        self.assertIsNone(report['status_code'])
        self.assertIsNone(report['error']['code'])
        self.assertIsNone(report['usage'])
        self.assertNotIn('PRIVATE-TIMEOUT',json.dumps(report))

    def test_nested_and_unknown_metadata_fail_closed(self):
        from types import SimpleNamespace
        result=diagnostic.filtered_error(SimpleNamespace(status_code=400,body={'error':{
            'code':'private-code','type':'secret','param':'unknown-sensitive-param',
            'message':'full sensitive input'}},code=None,type=None,param=None))
        self.assertEqual(result['error']['param'],'[filtered]')
        self.assertNotIn('sensitive',json.dumps(result))
        self.assertNotIn('private-code',json.dumps(result))

    def test_existing_output_prevents_any_client_creation(self):
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/'existing.json';output.write_text('{}')
            with patch.object(sys,'argv',['diag','--output',str(output)]),patch('openai.OpenAI') as sdk:
                with self.assertRaises(SystemExit):diagnostic.main()
                sdk.assert_not_called()

if __name__=='__main__':unittest.main()
