"""Suite guards and retries tested without real API calls."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from run_agent_suite import claim_case,check_identity,verify_test_lock,AuditedResponses,write_json

class SuiteTests(unittest.TestCase):
    def test_exclusive_case_marker_prevents_double_run(self):
        with tempfile.TemporaryDirectory() as d:
            claim_case(d,'q01')
            with self.assertRaises(FileExistsError):claim_case(d,'q01')

    def test_changed_config_or_code_rejected(self):
        check_identity({'identity':{'a':1}},{'a':1})
        with self.assertRaises(ValueError):check_identity({'identity':{'a':1}},{'a':2})

    def test_test_requires_lock(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):verify_test_lock(Path(d),{})

    def test_atomic_checkpoint_json(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'case.json';write_json(p,{'state':'done'})
            self.assertEqual(json.loads(p.read_text()),{'state':'done'})
            self.assertFalse(p.with_suffix('.json.tmp').exists())

    def test_transient_retry_is_bounded_and_audited(self):
        class APITimeoutError(Exception):pass
        class Fake:
            def __init__(self):self.responses=self;self.n=0
            def create(self,**kwargs):self.n+=1;raise APITimeoutError('private text must not be logged')
        with tempfile.TemporaryDirectory() as d:
            c=Fake();path=Path(d)/'attempts.jsonl'
            with self.assertRaises(APITimeoutError):AuditedResponses(c,path,{}).create(model='mock')
            self.assertEqual(c.n,2)
            text=path.read_text();self.assertNotIn('private text',text)
            events=[json.loads(x) for x in text.splitlines()]
            self.assertEqual(sum(e['event']=='api_attempt_started' for e in events),2)

    def test_auth_failure_never_retried(self):
        class Auth(Exception):status_code=401
        class Fake:
            def __init__(self):self.responses=self;self.n=0
            def create(self,**kwargs):self.n+=1;raise Auth('secret')
        with tempfile.TemporaryDirectory() as d:
            c=Fake()
            with self.assertRaises(Auth):AuditedResponses(c,Path(d)/'a.jsonl',{}).create()
            self.assertEqual(c.n,1)

if __name__=='__main__':unittest.main()
