"""Resumable version-locked DEV/TEST Agent evaluation. No labels enter inference."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'starter'))
from baseline import TfidfIndex
from benchmark_control import verify_frozen,digest
from openai_agent import OpenAIController,run_openai_agent
from retrievers import LocalEncoder,DenseRetriever,BM25Retriever,HybridRRFRetriever
from run_agent_dev import make_client

PROFILES={'baseline':{'retriever':'tfidf','budget_chars':800},
          'selected':{'retriever':'hybrid_rrf','budget_chars':2400}}
COMMON={'model':'gpt-4.1-mini','expected_model':'gpt-4.1-mini-2025-04-14',
        'max_searches':3,'top_k':3,'max_output_tokens':600,'timeout_seconds':60,
        'sdk_max_retries':0,'transient_retries_per_request':1,'temperature':0,
        'candidate_k_per_branch':20,'rrf_k':60,'metadata_filter':{},
        'run_id':'6bb5bbaae6bdc33389366d82272c71e10e29f07ed97a354d820799b60d0705d3'}
SOURCE_FILES=['src/run_agent_suite.py','src/openai_agent.py','src/grounding.py',
              'src/retrievers.py','src/run_agent_dev.py','src/evaluate_agent_suite.py',
              'starter/baseline.py','starter/agent_metrics.py','src/requirements.txt']


def now():return datetime.now(timezone.utc).isoformat()


def write_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temp.replace(path)


def source_hashes():return {name:digest(ROOT/name) for name in SOURCE_FILES}


def identity():return {'schema':'agent-suite-v1','common':COMMON,'profiles':PROFILES,
                        'code_sha256':source_hashes(),'benchmark_manifest_sha256':digest(ROOT/'data/benchmark_manifest.json')}


def claim_case(folder,case_id):
    """Exclusive claim marker prevents silent paid reruns, including after crashes."""
    marker=Path(folder)/(case_id+'.started.json')
    marker.parent.mkdir(parents=True,exist_ok=True)
    with marker.open('x',encoding='utf-8') as stream:json.dump({'query_id':case_id,'started_at':now()},stream)


def check_identity(saved,current):
    if saved['identity']!=current:raise ValueError('Code/config/benchmark changed; refuse mixing versions')


def verify_test_lock(output,current):
    lock_path=output/'final_config_lock.json'
    if not lock_path.is_file():raise ValueError('TEST prohibited until reviewed DEV and final config lock exist')
    lock=json.loads(lock_path.read_text(encoding='utf-8'))
    if lock['identity']!=current:raise ValueError('Final lock no longer matches code/config')
    for name,h in lock['dev_artifact_sha256'].items():
        if digest(output/name)!=h:raise ValueError('Locked DEV artifact changed')
    return lock


class AuditedResponses:
    def __init__(self,client,path,scope):self.client=client;self.path=Path(path);self.scope=scope
    def log(self,row):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.path.open('a',encoding='utf-8') as stream:
            stream.write(json.dumps({**self.scope,**row},ensure_ascii=False)+'\n');stream.flush()
    def create(self,**params):
        for retry in range(COMMON['transient_retries_per_request']+1):
            started=time.perf_counter()
            self.log({'event':'api_attempt_started','at':now(),'retry_index':retry})
            try:
                result=self.client.responses.create(**params)
            except Exception as exc:
                code=getattr(exc,'code',None)
                safe_code=code if code in {'insufficient_quota','rate_limit_exceeded','invalid_api_key','model_not_found'} else None
                status=getattr(exc,'status_code',None)
                transient=(type(exc).__name__ in {'APITimeoutError','APIConnectionError'} or status==429 or (isinstance(status,int) and status>=500)) and safe_code!='insufficient_quota'
                self.log({'event':'api_attempt_error','at':now(),'retry_index':retry,'type':type(exc).__name__,
                          'status_code':status,'code':safe_code,'request_id':getattr(exc,'request_id',None),
                          'latency_ms':(time.perf_counter()-started)*1000,'usage':None,'will_retry':transient and retry==0})
                if transient and retry==0:time.sleep(1);continue
                raise
            usage=result.usage.model_dump() if result.usage else None
            self.log({'event':'api_attempt_success','at':now(),'retry_index':retry,'actual_model':result.model,
                      'status':result.status,'request_id':getattr(result,'_request_id',None),'usage':usage,
                      'latency_ms':(time.perf_counter()-started)*1000})
            return result


class AuditedClient:
    def __init__(self,client,path,scope):self.responses=AuditedResponses(client,path,scope)


def interrupted_trace(case,profile):
    return {'query_id':case['id'],'question':case['question'],'split':case['split'],'configuration':profile,
            'status':'error','reason':'interrupted_case_not_automatically_rerun','error':{'type':'InterruptedCase'},
            'answer':'','citations':[],'events':[],'context':'','context_ids':[],
            'model_calls':[],'elapsed_ms':None,'usage':None,'original_query_results':[],
            'note':'Inspect append-only API attempts for possible completed/unknown billable calls.'}


def export_traces(folder):
    rows=[json.loads(p.read_text(encoding='utf-8')) for p in sorted((folder/'cases').glob('*.json')) if not p.name.endswith('.started.json')]
    write_json(folder/'traces.json',rows)
    return rows


def load_original_cache():
    rows=json.loads((ROOT/'report/individual/checkpoint3a/traces.json').read_text(encoding='utf-8'))
    return {(t['query_id'],t['strategy']):t for t in rows if t['budget_chars']==2400}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--split',required=True,choices=['dev','test'])
    p.add_argument('--output',type=Path,default=ROOT/'report/individual/final-evaluation')
    p.add_argument('--resume',action='store_true')
    p.add_argument('--day6',type=Path,default=Path('D:/VinUniAI/K5-L3B-Day06-2A202603829-DataIngestionEngineering'))
    args=p.parse_args();verify_frozen();current=identity();output=args.output
    if args.split=='test':verify_test_lock(output,current)
    manifest_path=output/'suite_manifest.json'
    if manifest_path.exists():
        if not args.resume:raise SystemExit('Existing suite: use explicit --resume; completed cases will never rerun')
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'));check_identity(manifest,current)
    else:
        if args.split!='dev':raise ValueError('DEV suite must exist first')
        manifest={'created_at':now(),'identity':current,'selection_criteria':'DEV complete evidence; grounded answer and valid citations; false abstention; token cost/latency. Retrieval chosen from original-query comparison. No prompt/validator tuning during this suite.'}
        write_json(manifest_path,manifest)
        for name in SOURCE_FILES:
            destination=output/'source_snapshot'/name;destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/name,destination)
    # Select split before inspecting any question text. No gold loaded here.
    cases=[c for c in json.loads((ROOT/'data/agent_cases.json').read_text(encoding='utf-8')) if c['split']==args.split]
    if len(cases)!=(17 if args.split=='dev' else 7):raise ValueError('Unexpected split membership')
    if args.split=='test':
        marker=output/'test_started.json'
        if not marker.exists():
            with marker.open('x',encoding='utf-8') as f:json.dump({'started_at':now(),'lock_sha256':digest(output/'final_config_lock.json'),'case_ids':[c['id'] for c in cases]},f)
        elif not args.resume:raise ValueError('TEST already started; no second TEST pass')
    from dotenv import load_dotenv
    load_dotenv(ROOT/'.env',override=False,encoding='utf-8-sig')
    if not os.getenv('OPENAI_API_KEY','').strip():raise SystemExit('OPENAI_API_KEY missing')
    load_dotenv(args.day6/'starter/.env',override=False)
    started=time.perf_counter();client=make_client(timeout=COMMON['timeout_seconds'])
    chunks=json.loads((ROOT/'data/chunks.json').read_text(encoding='utf-8'));lookup={c['id']:c for c in chunks}
    encoder=LocalEncoder(args.day6/'models/all-MiniLM-L6-v2')
    dense=DenseRetriever(os.environ['DATABASE_URL'],COMMON['run_id'],encoder,chunks)
    methods={'baseline':TfidfIndex(chunks),'selected':HybridRRFRetriever(dense,BM25Retriever(chunks),candidate_k=20,rrf_k=60)}
    before=dense.snapshot();cache=load_original_cache() if args.split=='dev' else {}
    runtime={'split':args.split,'started_at':now(),'status':'running','identity':current,'model_fingerprint':encoder.fingerprint,
             'database_before_sha256':before,'profiles':{},'transient_retry_policy':'at most one retry per transient failed API call; each attempt logged; no whole-case/test reruns'}
    try:
        for profile in ['selected','baseline']:
            folder=output/args.split/profile;case_dir=folder/'cases';case_dir.mkdir(parents=True,exist_ok=True)
            for case in cases:
                result_path=case_dir/(case['id']+'.json');marker=case_dir/(case['id']+'.started.json')
                if result_path.exists():continue
                if marker.exists():
                    write_json(result_path,interrupted_trace(case,profile));export_traces(folder);continue
                claim_case(case_dir,case['id'])
                api_log=output/'api_attempts.jsonl'
                wrapped=AuditedClient(client,api_log,{'split':args.split,'configuration':profile,'query_id':case['id']})
                controller=OpenAIController(wrapped,model=COMMON['model'],max_searches=COMMON['max_searches'],max_output_tokens=COMMON['max_output_tokens'])
                raw_cached=cache.get((case['id'],PROFILES[profile]['retriever']))
                if raw_cached and raw_cached['question']==case['question']:
                    original=[{**lookup[c['id']],'score':c['score']} for c in raw_cached['results']]
                    raw_source='reused original-query DEV ranking from checkpoint3a; no labels enter Agent'
                else:
                    original=methods[profile].search(case['question'],top_k=3)
                    raw_source='original-query independent retrieval; not passed to Agent'
                trace=run_openai_agent(case['question'],controller,methods[profile],max_searches=3,top_k=3,budget=PROFILES[profile]['budget_chars'])
                trace.update(query_id=case['id'],question=case['question'],split=args.split,configuration=profile,
                             original_query_results=original,original_query_provenance=raw_source,case_finished_at=now())
                write_json(result_path,trace);rows=export_traces(folder)
                print(json.dumps({'split':args.split,'config':profile,'id':case['id'],'status':trace['status'],
                                  'reason':trace.get('reason'),'searches':len(trace.get('search_queries',[])),'usage':trace.get('usage')},ensure_ascii=False),flush=True)
                if trace['status']=='error' and (trace.get('error') or {}).get('status_code') in (400,401,403,404):
                    raise RuntimeError('Non-transient provider error; stopped safely with checkpoints')
            runtime['profiles'][profile]={'completed_cases':len(export_traces(folder))}
        runtime['status']='completed_pending_review'
    finally:
        runtime['elapsed_seconds_including_setup']=time.perf_counter()-started
        runtime['finished_at']=now();runtime['database_after_sha256']=dense.snapshot()
        runtime['database_unchanged']=runtime['database_before_sha256']==runtime['database_after_sha256']
        verify_frozen();check_identity(manifest,identity())
        write_json(output/args.split/'runtime.json',runtime);client.close()
        if not runtime['database_unchanged']:raise RuntimeError('Database snapshot changed')
    if args.split=='test':write_json(output/'test_completed.json',{'completed_at':now(),'lock_sha256':digest(output/'final_config_lock.json'),'status':runtime['status']})

if __name__=='__main__':main()
