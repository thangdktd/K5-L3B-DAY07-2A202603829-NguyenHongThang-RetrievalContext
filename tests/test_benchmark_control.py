import json
import sys
import tempfile
import subprocess
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from benchmark_control import digest, verify_frozen, validate_all
from build_final_benchmark import build

class BenchmarkControlTests(unittest.TestCase):
    def test_rebuild_matches_current_annotations(self):
        questions,cases = build()
        self.assertEqual(questions,json.loads((ROOT/'data/questions.json').read_text(encoding='utf-8')))
        self.assertEqual(cases,json.loads((ROOT/'data/agent_cases.json').read_text(encoding='utf-8')))
        chunks=json.loads((ROOT/'data/chunks.json').read_text(encoding='utf-8'))
        self.assertEqual(validate_all(chunks,questions,cases)['cases'],24)

    def test_frozen_and_retired_writers_refuse_to_overwrite(self):
        protected=['data/chunks.json','data/questions.json','data/agent_cases.json','data/benchmark_manifest.json']
        before={name:digest(ROOT/name) for name in protected}
        for script in ['src/build_final_benchmark.py','src/prepare_data.py','scratch/build_benchmark.py']:
            result=subprocess.run([sys.executable,'-X','utf8',str(ROOT/script)],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
            self.assertNotEqual(result.returncode,0,script)
        self.assertEqual(before,{name:digest(ROOT/name) for name in protected})

    def test_freeze_hash_guard_detects_tampering(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'data').mkdir(); target=root/'data/example.json'
            target.write_text('[]',encoding='utf-8')
            (root/'data/benchmark_manifest.json').write_text(json.dumps({'files':{'data/example.json':{'sha256':digest(target)}}}),encoding='utf-8')
            verify_frozen(root)
            target.write_text('[1]',encoding='utf-8')
            with self.assertRaises(ValueError): verify_frozen(root)

if __name__=='__main__': unittest.main()
