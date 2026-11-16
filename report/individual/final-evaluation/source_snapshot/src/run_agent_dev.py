"""Real OpenAI Agent DEV run. TEST has no execution path in this program."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'starter'))
from baseline import evidence_complete
from benchmark_control import verify_frozen,digest
from openai_agent import OpenAIController,run_openai_agent
from retrievers import LocalEncoder,DenseRetriever,BM25Retriever,HybridRRFRetriever


def load_dev_cases(path):
    cases=[c for c in json.loads(Path(path).read_text(encoding='utf-8')) if c['split']=='dev']
    if len(cases)!=17 or len({c['id'] for c in cases})!=17:raise ValueError('Expected 17 unique DEV cases')
    return cases


def make_client(timeout=45.0):
    import logging
    for name in ('openai','httpx','httpx2','httpcore','httpcore2'):
        logging.getLogger(name).setLevel(logging.WARNING)
    from openai import OpenAI
    key=os.getenv('OPENAI_API_KEY','').strip()
    if not key:raise ValueError('OPENAI_API_KEY is missing; configure environment or root .env, never print it')
    return OpenAI(api_key=key,base_url='https://api.openai.com/v1',max_retries=0,timeout=timeout)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    selection=p.add_mutually_exclusive_group()
    selection.add_argument('--q01',action='store_true',help='Run only q01 DEV, max 2 searches, 250 output tokens, timeout 60s')
    selection.add_argument('--q12',action='store_true',help='Run only q12 DEV, max 3 searches, 250 output tokens, timeout 60s')
    selection.add_argument('--pilot',action='store_true',help='Run exactly q01, q12, q_unans_dev_01; never full DEV')
    p.add_argument('--model',default='gpt-4.1-mini')
    p.add_argument('--day6',type=Path,default=Path('D:/VinUniAI/K5-L3B-Day06-2A202603829-DataIngestionEngineering'))
    p.add_argument('--output',type=Path,default=ROOT/'report/individual/checkpoint3b')
    args=p.parse_args()
    from dotenv import load_dotenv
    load_dotenv(ROOT/'.env',override=False,encoding='utf-8-sig')
    # Check credentials before loading local models, creating outputs, or calling API.
    if not os.getenv('OPENAI_API_KEY','').strip():raise SystemExit('OPENAI_API_KEY missing: configure environment or Day 07 root .env; no API request sent.')
    verify_frozen()
    if args.output.exists():raise SystemExit('Output already exists; use a new --output directory')
    max_searches=2 if args.q01 else 3
    timeout=60.0 if (args.q01 or args.q12) else 45.0
    client=make_client(timeout=timeout)
    # This environment file is used only for the local Day 06 DB connection.
    load_dotenv(args.day6/'starter/.env',override=False)
    cases=load_dev_cases(ROOT/'data/agent_cases.json')
    if args.q01:
        cases=[c for c in cases if c['id']=='q01']
        if len(cases)!=1:raise ValueError('Expected exactly q01 DEV')
    if args.q12:
        cases=[c for c in cases if c['id']=='q12']
        if len(cases)!=1:raise ValueError('Expected exactly q12 DEV')
    if args.pilot:
        selected_ids=('q01','q12','q_unans_dev_01')
        lookup_cases={c['id']:c for c in cases}
        cases=[lookup_cases[cid] for cid in selected_ids]
        if len(cases)!=3 or any(c['split']!='dev' for c in cases):raise ValueError('Invalid pilot membership')
    output_token_limit=250 if (args.q01 or args.q12) else (600 if args.pilot else 900)
    chunks=json.loads((ROOT/'data/chunks.json').read_text(encoding='utf-8'))
    encoder=LocalEncoder(args.day6/'models/all-MiniLM-L6-v2')
    dense=DenseRetriever(os.environ['DATABASE_URL'],'6bb5bbaae6bdc33389366d82272c71e10e29f07ed97a354d820799b60d0705d3',encoder,chunks)
    hybrid=HybridRRFRetriever(dense,BM25Retriever(chunks),candidate_k=20,rrf_k=60)
    before=dense.snapshot();traces=[];started=time.perf_counter()
    args.output.mkdir(parents=True,exist_ok=False)
    runtime={'status':'running','requested_model':args.model,'split':'dev','pilot':args.pilot,'q01_only':args.q01,'q12_only':args.q12,'selected_case_ids':[c['id'] for c in cases],'test_queries_run':0,
             'config':{'max_searches':max_searches,'top_k':3,'budget_chars':2400,'dedup':'chunk_id','packing':'newest search first, full chunks; source_id/page/id header',
                       'rrf_k':60,'candidate_k_per_branch':20,'temperature':0,'max_output_tokens':output_token_limit,'provider_timeout_seconds':timeout,'provider_retries':0},
             'benchmark_manifest_sha256':digest(ROOT/'data/benchmark_manifest.json'),
             'model_fingerprint':encoder.fingerprint,'database_read_only':True,
             'implementation_sha256':{f:digest(ROOT/f) for f in ['src/openai_agent.py','src/grounding.py','src/run_agent_dev.py']},
             'review_status':'pending direct review of answers against cited context; ID matching alone is not grounding',
             'cost_usd':None,'cost_note':'Compute from actual model usage and verified pricing; not an invoice'}
    try:
        for case in cases:
            controller=OpenAIController(client,model=args.model,max_searches=max_searches,max_output_tokens=output_token_limit)
            # Only the question string enters the Agent: no gold, answerable flag,
            # absence reason, expected behavior, or benchmark ID is sent to OpenAI.
            trace=run_openai_agent(case['question'],controller,hybrid,max_searches=max_searches,top_k=3,budget=2400)
            trace.update(query_id=case['id'],question=case['question'],split='dev')
            traces.append(trace)
            (args.output/'traces.json').write_text(json.dumps(traces,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            print(json.dumps({'query_id':case['id'],'status':trace['status'],'searches':len(trace['search_queries']),
                              'elapsed_ms':round(trace['elapsed_ms']),'usage':trace['usage']}),flush=True)
            if trace['status']=='error':
                runtime['status']='stopped_on_error';break
        else:runtime['status']='completed_pending_review'
    finally:
        after=dense.snapshot();verify_frozen()
        runtime.update(database_unchanged=before==after,database_before_sha256=before,database_after_sha256=after,
                       completed_cases=len(traces),not_run_case_ids=[c['id'] for c in cases if c['id'] not in {t['query_id'] for t in traces}],
                       elapsed_seconds=time.perf_counter()-started,
                       usage={k:sum(t['usage'][k] for t in traces) for k in ('input_tokens','output_tokens','cached_input_tokens')},
                       search_count_distribution=dict(Counter(len(t['search_queries']) for t in traces)))
        actual_models=sorted({call['actual_model'] for trace in traces for call in trace['model_calls'] if call.get('event')=='model_call'})
        runtime['actual_models']=actual_models
        runtime['api_requests']=sum(len(t['model_calls']) for t in traces)
        runtime['successful_api_responses']=sum(c['event']=='model_call' for t in traces for c in t['model_calls'])
        runtime['usage_missing_calls']=sum(t['usage_missing_calls'] for t in traces)
        if actual_models and all(name=='gpt-4.1-mini' or name.startswith('gpt-4.1-mini-') for name in actual_models) and runtime['usage_missing_calls']==0:
            u=runtime['usage']
            runtime['cost_usd']=((u['input_tokens']-u['cached_input_tokens'])*0.4+u['cached_input_tokens']*0.1+u['output_tokens']*1.6)/1_000_000
            runtime['cost_basis']={'source':'https://developers.openai.com/api/docs/models/gpt-4.1-mini','checked_on':'2026-11-16',
                                   'usd_per_million':{'input':0.4,'cached_input':0.1,'output':1.6},'type':'estimate, not billing invoice'}
        (args.output/'runtime.json').write_text(json.dumps(runtime,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        client.close()
        if before!=after:raise RuntimeError('Day 06 database changed')
    # Evaluation-only phase after all provider calls. Gold is never passed to the controller.
    questions={q['id']:q for q in json.loads((ROOT/'data/questions.json').read_text(encoding='utf-8')) if q['split']=='dev'}
    lookup={c['id']:c for c in chunks}
    context_reviews=[];reviews=[]
    for trace in traces:
        cid=trace['query_id'];q=questions.get(cid)
        if q:
            context_reviews.append({'query_id':cid,'context_evidence_complete':evidence_complete([lookup[i] for i in trace['context_ids']],q)})
        if trace['status']=='error':continue
        r={'query_id':cid,'citation_support':[None for _ in trace['citations']],'reason':'PENDING direct review; do not infer support from IDs'}
        r['answer_grade' if q else 'abstention_correct']=None
        reviews.append(r)
    (args.output/'context_metrics.json').write_text(json.dumps(context_reviews,indent=2)+'\n',encoding='utf-8')
    (args.output/'reviews_template.json').write_text(json.dumps(reviews,indent=2)+'\n',encoding='utf-8')
    if runtime['status']=='stopped_on_error':raise SystemExit('Agent stopped on error; inspect sanitized traces. No automatic retry or fallback model.')

if __name__=='__main__':main()
