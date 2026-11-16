"""Post-inference evaluation and pre-TEST locking; no API or retrieval calls."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import json
from pathlib import Path
import statistics
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'starter'))
from agent_metrics import aggregate
from baseline import evidence_complete
from benchmark_control import verify_frozen,digest
from run_agent_suite import identity,check_identity,write_json,PROFILES


def ratio(n,N):return {'n':n,'N':N,'rate':n/N if N else None}


def evaluate(output,split,prepare=False):
    verify_frozen()
    cases=[c for c in json.loads((ROOT/'data/agent_cases.json').read_text(encoding='utf-8')) if c['split']==split]
    questions={q['id']:q for q in json.loads((ROOT/'data/questions.json').read_text(encoding='utf-8')) if q['split']==split}
    chunks={c['id']:c for c in json.loads((ROOT/'data/chunks.json').read_text(encoding='utf-8'))}
    assert len(cases)==(17 if split=='dev' else 7)
    summaries={}
    for profile in PROFILES:
        folder=output/split/profile
        traces=json.loads((folder/'traces.json').read_text(encoding='utf-8'))
        if {t['query_id'] for t in traces}!={c['id'] for c in cases} or any(t['split']!=split for t in traces):raise ValueError('Incomplete/mixed split')
        byid={t['query_id']:t for t in traces};diagnostics=[];template=[]
        for case in cases:
            t=byid[case['id']];q=questions.get(case['id'])
            searches=[e for e in t['events'] if e['event']=='search']
            raw=t.get('original_query_results',[])
            first=searches[0]['results'] if searches else []
            context=[chunks[cid] for cid in t.get('context_ids',[])]
            row={'query_id':case['id'],'answerable':case['answerable'],'status':t['status'],'reason':t.get('reason'),
                 'searches':len(searches),'original_query_hit1':evidence_complete(raw[:1],q) if q else None,
                 'original_query_hit3':evidence_complete(raw[:3],q) if q else None,
                 'agent_first_query_hit1':evidence_complete(first[:1],q) if q else None,
                 'agent_first_query_hit3':evidence_complete(first[:3],q) if q else None,
                 'context_evidence_complete':evidence_complete(context,q) if q else None,
                 'citation_ids_in_context':all(cid in t.get('context_ids',[]) for cid in t['citations']),
                 'final_answer':t['answer'],'context_ids':t.get('context_ids',[])}
            diagnostics.append(row)
            if t['status']=='error':continue
            review={'query_id':case['id'],'citation_support':[None for _ in t['citations']],
                    'context_grade':None if q else 'not_applicable','reason':'PENDING direct review of final output and supporting context'}
            review['answer_grade' if q else 'abstention_correct']=None
            template.append(review)
        write_json(folder/'retrieval_context_diagnostics.json',diagnostics)
        if prepare:
            if not (folder/'reviews_template.json').exists():write_json(folder/'reviews_template.json',template)
            continue
        reviews=json.loads((folder/'reviews.json').read_text(encoding='utf-8'))
        for review in reviews:
            if not review.get('reason') or 'PENDING' in review['reason']:raise ValueError('Unreviewed case')
            if review['query_id'] in questions and review.get('context_grade') not in (0,1,2):raise ValueError('Missing manual context grade')
        result=aggregate(cases,traces,reviews)
        answerable=[d for d in diagnostics if d['answerable']]
        result.update(split=split,configuration=profile,
                      ranking={key:ratio(sum(d[key] for d in answerable),len(answerable)) for key in ['original_query_hit1','original_query_hit3','agent_first_query_hit1','agent_first_query_hit3','context_evidence_complete']},
                      error_breakdown=dict(Counter(t.get('reason') for t in traces if t['status']=='error')),
                      abstention_reasons=dict(Counter(t.get('reason') for t in traces if t['status']=='abstain')),
                      search_distribution=dict(Counter(d['searches'] for d in diagnostics)),
                      manual_context_grades=dict(Counter(str(r['context_grade']) for r in reviews if r['query_id'] in questions)),
                      median_agent_ms=statistics.median(t['elapsed_ms'] for t in traces if t.get('elapsed_ms') is not None),
                      reviewer='assistant direct source/final-output review; not an independent human or LLM judge',
                      provider_errors_note='starter aggregate names all error statuses provider_errors; use error_breakdown for correct classification')
        if (output/'api_attempts.jsonl').exists():
            calls=[json.loads(line) for line in (output/'api_attempts.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
            calls=[c for c in calls if c['split']==split and c['configuration']==profile]
            successes=[c for c in calls if c['event']=='api_attempt_success'];usage=[c['usage'] for c in successes if c.get('usage')]
            I=sum(u.get('input_tokens',0) for u in usage);O=sum(u.get('output_tokens',0) for u in usage)
            C=sum((u.get('input_tokens_details') or {}).get('cached_tokens',0) for u in usage)
            result['api']={'attempts':sum(c['event']=='api_attempt_started' for c in calls),'successful_responses':len(successes),
                           'failed_attempts':sum(c['event']=='api_attempt_error' for c in calls),
                           'input_tokens_known':I,'output_tokens_known':O,'cached_input_tokens_known':C,
                           'estimated_known_token_cost_usd':((I-C)*0.4+C*0.1+O*1.6)/1e6,
                           'failed_or_missing_usage_cost_unknown':any(c['event']=='api_attempt_error' or c.get('usage') is None for c in calls if c['event']!='api_attempt_started'),
                           'provider_latency_ms_sum':sum(c['latency_ms'] for c in successes),
                           'pricing_source':'https://developers.openai.com/api/docs/models/gpt-4.1-mini','price_checked':'2026-11-16',
                           'invoice':False}
        write_json(folder/'metrics.json',result);summaries[profile]=result
    if not prepare:write_json(output/split/'summary.json',summaries)
    return summaries


def lock_final(output):
    if (output/'test_started.json').exists():raise ValueError('TEST already started; lock cannot change')
    lock_path=output/'final_config_lock.json'
    if lock_path.exists():raise ValueError('Final config already locked')
    current=identity();check_identity(json.loads((output/'suite_manifest.json').read_text(encoding='utf-8')),current)
    summaries=evaluate(output,'dev')
    for profile in PROFILES:
        if summaries[profile]['cases']!=17:raise ValueError('DEV not complete')
    names=['dev/summary.json']+[f'dev/{p}/{f}' for p in PROFILES for f in ['traces.json','reviews.json','metrics.json']]
    lock={'locked_at':datetime.now(timezone.utc).isoformat(),'identity':current,
          'selected':'selected','baseline':'baseline',
          'selection_basis':'Hybrid2400 original-query retrieval/context DEV coverage versus TF-IDF800; grounded/citation and false-abstention DEV review considered; no validator/prompt tuning. Partial answer quality is reported honestly.',
          'dev_artifact_sha256':{name:digest(output/name) for name in names},
          'test_protocol':'Both profiles each of 7 TEST cases once; checkpoint/resume missing cases only; no tuning after test_started; at most one transient call retry logged'}
    write_json(lock_path,lock)
    return lock


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'report/individual/final-evaluation')
    p.add_argument('--split',choices=['dev','test'],default='dev')
    p.add_argument('--prepare-reviews',action='store_true')
    p.add_argument('--lock',action='store_true')
    args=p.parse_args()
    if args.lock:lock_final(args.output);print('Final configuration locked BEFORE TEST')
    else:
        s=evaluate(args.output,args.split,args.prepare_reviews)
        print(json.dumps(s,ensure_ascii=False,indent=2) if s else 'Review templates prepared, no API calls')

if __name__=='__main__':main()
