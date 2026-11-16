"""DEV-only comparison; no agent and no TEST execution option."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import statistics
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'starter'))
from baseline import TfidfIndex, evaluate, evidence_groups
from benchmark_control import verify_frozen, digest
from retrievers import BM25Retriever, DenseRetriever, HybridRRFRetriever, LocalEncoder


def summary(traces):
    def metrics(rows):
        n=len(rows)
        return {'N':n,**{key:{'n':sum(t[key] for t in rows),'N':n,'rate':sum(t[key] for t in rows)/n if n else None} for key in ('hit1','hit3','context_hit')}}
    return {**metrics(traces),'single_group':metrics([t for t in traces if len(t['gold_groups'])==1]),
            'multi_group':metrics([t for t in traces if len(t['gold_groups'])>1]),
            'median_ms':statistics.median(t['elapsed_ms'] for t in traces),
            'avg_context_chars':statistics.mean(t['context_chars'] for t in traces)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--day6',type=Path,default=Path('D:/VinUniAI/K5-L3B-Day06-2A202603829-DataIngestionEngineering'))
    p.add_argument('--run-id',default='6bb5bbaae6bdc33389366d82272c71e10e29f07ed97a354d820799b60d0705d3')
    p.add_argument('--output',type=Path,default=ROOT/'report/individual/checkpoint3a')
    args=p.parse_args()
    frozen=verify_frozen()
    # Reject nonlocal network even if a model library unexpectedly tries to connect.
    def guard(event, args):
        if event=='socket.connect' and (not isinstance(args[1],tuple) or args[1][0] not in ('127.0.0.1','::1')):
            raise RuntimeError('External network prohibited')
        if event=='socket.getaddrinfo' and args[0] not in ('localhost','127.0.0.1','::1'):
            raise RuntimeError('External DNS prohibited')
        if event=='socket.sendto': raise RuntimeError('Datagrams prohibited')
    sys.addaudithook(guard)
    from dotenv import load_dotenv
    load_dotenv(args.day6/'starter/.env')
    chunks=json.loads((ROOT/'data/chunks.json').read_text(encoding='utf-8'))
    questions=[q for q in json.loads((ROOT/'data/questions.json').read_text(encoding='utf-8')) if q['split']=='dev']
    if len(questions)!=15:raise ValueError('Expected 15 DEV answerable questions')
    started=time.perf_counter()
    encoder=LocalEncoder(args.day6/'models/all-MiniLM-L6-v2')
    dense=DenseRetriever(os.environ['DATABASE_URL'],args.run_id,encoder,chunks)
    before=dense.snapshot()
    # Generate only original DEV question embeddings. Warm shared cache makes search
    # timings exclude encoder initialization and embedding, both reported separately.
    t=time.perf_counter()
    for q in questions: encoder.embed_query(q['question'])
    embed_seconds=time.perf_counter()-t
    bm25=BM25Retriever(chunks)
    methods={'tfidf':TfidfIndex(chunks),'dense':dense,'bm25':bm25,
             'hybrid_rrf':HybridRRFRetriever(dense,bm25,candidate_k=20,rrf_k=60)}
    initialization_seconds=time.perf_counter()-started
    all_traces=[];configs={}
    for budget in (800,2400):
        for name,retriever in methods.items():
            key=f'{name}-b{budget}'
            traces=evaluate(retriever,questions,budget=budget)
            for trace in traces:
                trace.update(strategy=name,configuration=key,query_mode='original',applied_filter={},
                             model_called=False,context_sent_to_model=False)
            configs[key]=summary(traces)
            all_traces.extend(traces)
            print(json.dumps({'configuration':key,**{k:configs[key][k] for k in ('hit1','hit3','context_hit')}}),flush=True)
    after=dense.snapshot()
    if before!=after: raise ValueError('Database snapshot changed')
    verify_frozen()
    report={'status':'passed','split':'dev','answerable_questions':15,'unanswerable_excluded_from_retrieval_metrics':2,
            'test_queries_run':0,'agent_calls':0,'generated_query_embeddings':len(encoder.cache),
            'model':encoder.name,'model_fingerprint':encoder.fingerprint,'dimensions':384,
            'run_id':args.run_id,'stored_strategy':'B','database_read_only':True,'database_unchanged':before==after,
            'database_before_sha256':before,'database_after_sha256':after,'frozen_manifest_sha256':digest(ROOT/'data/benchmark_manifest.json'),
            'query_embedding_seconds':embed_seconds,'initialization_seconds':initialization_seconds,
            'latency_scope':'warm query embedding cache; search + context packing; excludes evidence scoring, initial model load and query encoding',
            'context_unit':'characters including headers and separators; full rank-ordered chunks, skip if not fit',
            'tokens':'not measured; no LLM called','external_service_cost_usd':0,
            'parameters':{'bm25':{'k1':1.5,'b':0.75,'tokens':'baseline NFC casefold word tokens; query terms deduplicated'},
                          'dense':{'distance':'exact cosine','filter':{},'tie_break':'chunk_id'},
                          'hybrid_rrf':{'candidate_k_per_method':20,'rrf_k':60,'formula':'sum(1/(60+rank)), ranks 1-based'},
                          'top_k':3,'context_budgets':[800,2400]},
            'selection_criteria':'DEV Evidence Hit@3, then Context Evidence Rate, then Hit@1, then latency; provisional retrieval choice only; no final Agent configuration selected',
            'hypotheses':['BM25 saturation/length normalization may improve lexical ranking over TF-IDF.',
                          'RRF may combine lexical and semantic evidence without incompatible score scales.',
                          '2400-character budget may retain evidence omitted by 800-character budget without changing ranking.'],
            'configurations':configs,'elapsed_seconds':time.perf_counter()-started,
            'implementation_sha256':{f:digest(ROOT/f) for f in ['src/retrievers.py','src/evaluate_retrieval.py']}}
    args.output.mkdir(parents=True,exist_ok=False)
    for name,value in [('metrics.json',report),('traces.json',all_traces)]:
        (args.output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('DEV comparison saved; database and frozen benchmark unchanged',flush=True)

if __name__=='__main__':main()
