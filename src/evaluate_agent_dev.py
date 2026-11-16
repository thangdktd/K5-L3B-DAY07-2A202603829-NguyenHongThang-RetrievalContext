"""Aggregate explicitly reviewed DEV Agent results; never auto-grade grounding."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'starter'))
from agent_metrics import aggregate
from benchmark_control import verify_frozen
from run_agent_dev import load_dev_cases


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--reviews',type=Path,required=True)
    args=p.parse_args();verify_frozen()
    traces=json.loads((args.run/'traces.json').read_text(encoding='utf-8'))
    if any(t['split']!='dev' for t in traces):raise ValueError('Only DEV traces permitted')
    reviews=json.loads(args.reviews.read_text(encoding='utf-8'))
    if any(not r.get('reason') or 'PENDING' in r['reason'] for r in reviews):raise ValueError('Complete direct review and rationale before aggregation')
    # Missing/null labels are rejected by the reused official starter aggregator.
    result={'split':'dev','grading':'direct review labels; not a model judge; independent human confirmation still recommended',
            **aggregate(load_dev_cases(ROOT/'data/agent_cases.json'),traces,reviews)}
    (args.run/'agent_metrics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
