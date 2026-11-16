"""Day 07 retrieval adapters. Inputs are corpus/query only; benchmark gold is excluded."""
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'starter'))
from baseline import tokenize


def check_k(top_k):
    if type(top_k) is not int or top_k < 1:
        raise ValueError('top_k must be a positive integer')


class BM25Retriever:
    """Okapi BM25 with positive Robertson IDF, NFC/casefold word tokens."""
    def __init__(self, chunks, k1=1.5, b=0.75):
        if not chunks or k1 <= 0 or not 0 <= b <= 1:
            raise ValueError('Invalid BM25 corpus/parameters')
        self.chunks, self.k1, self.b = chunks, k1, b
        self.counts = [Counter(tokenize(c['text'])) for c in chunks]
        self.lengths = [sum(c.values()) for c in self.counts]
        self.avg_length = sum(self.lengths)/len(chunks) or 1
        df = Counter(t for c in self.counts for t in c)
        self.idf = {t: math.log(1+(len(chunks)-n+0.5)/(n+0.5)) for t,n in df.items()}

    def search(self, query, top_k=3):
        check_k(top_k)
        terms = set(tokenize(query))
        results = []
        for chunk, counts, length in zip(self.chunks, self.counts, self.lengths):
            normalizer = self.k1*(1-self.b+self.b*length/self.avg_length)
            score = sum(self.idf[t]*counts[t]*(self.k1+1)/(counts[t]+normalizer)
                        for t in terms if counts[t])
            if score > 0:
                results.append({**chunk, 'score': score, 'strategy': 'bm25'})
        return sorted(results,key=lambda c:(-c['score'],c['id']))[:top_k]


class HybridRRFRetriever:
    def __init__(self, dense, lexical, candidate_k=20, rrf_k=60):
        check_k(candidate_k)
        if rrf_k <= 0: raise ValueError('rrf_k must be positive')
        self.dense, self.lexical = dense, lexical
        self.candidate_k, self.rrf_k = candidate_k, rrf_k

    def search(self, query, top_k=3):
        check_k(top_k)
        candidates = max(top_k,self.candidate_k)
        merged = {}
        for name, retriever in [('dense',self.dense),('bm25',self.lexical)]:
            seen = set()
            for rank,c in enumerate(retriever.search(query,top_k=candidates),1):
                if c['id'] in seen: continue
                seen.add(c['id'])
                item = merged.setdefault(c['id'], {**c,'score':0.0,'strategy':'hybrid_rrf','component_ranks':{},'component_scores':{}})
                item['score'] += 1/(self.rrf_k+rank)
                item['component_ranks'][name] = rank
                item['component_scores'][name] = c['score']
        return sorted(merged.values(), key=lambda c:(-c['score'],c['id']))[:top_k]


def model_fingerprint(path):
    path=Path(path)
    entries=[(p.relative_to(path).as_posix(),hashlib.sha256(p.read_bytes()).hexdigest())
             for p in sorted(path.rglob('*')) if p.is_file() and '.cache' not in p.parts]
    return hashlib.sha256(json.dumps(entries,sort_keys=True).encode('utf-8')).hexdigest()


class LocalEncoder:
    name='sentence-transformers/all-MiniLM-L6-v2'
    dimensions=384
    def __init__(self, path):
        path=Path(path).resolve()
        if not (path/'modules.json').is_file(): raise ValueError('Local model missing')
        for name in ('HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE','HF_HUB_DISABLE_TELEMETRY','DO_NOT_TRACK'):
            os.environ[name]='1'
        from sentence_transformers import SentenceTransformer
        self.model=SentenceTransformer(str(path),device='cpu',local_files_only=True,trust_remote_code=False)
        if self.model.get_sentence_embedding_dimension()!=self.dimensions:
            raise ValueError('Model dimension mismatch')
        self.fingerprint=model_fingerprint(path)
        self.cache={}

    def embed_query(self, query):
        if not query.strip(): raise ValueError('Empty dense query')
        if query not in self.cache:
            ids=self.model.tokenizer(query,truncation=False,add_special_tokens=True)['input_ids']
            if len(ids)>self.model.max_seq_length: raise ValueError('Query exceeds model token limit')
            self.cache[query]=self.model.encode([query],normalize_embeddings=True,convert_to_numpy=True,show_progress_bar=False)[0].tolist()
        return self.cache[query]


class DenseRetriever:
    """Exact pgvector cosine search restricted to one Day 06 strategy B run."""
    def __init__(self, database_url, run_id, encoder, chunks):
        from psycopg.conninfo import conninfo_to_dict
        options=conninfo_to_dict(database_url)
        if options.get('service') or any(x not in ('localhost','127.0.0.1','::1') for x in options.get('host','').split(',')):
            raise ValueError('Only explicit loopback database hosts permitted')
        if any(x and x not in ('127.0.0.1','::1') for x in options.get('hostaddr','').split(',')):
            raise ValueError('Non-loopback hostaddr prohibited')
        self.url,self.run_id,self.encoder=database_url,run_id,encoder
        self.chunks={c['id']:c for c in chunks}
        with self.connect() as connection:
            row=connection.execute('SELECT model_name,model_fingerprint,dimensions FROM ingestion_runs WHERE run_id=%s',(run_id,)).fetchone()
            if row!=(encoder.name,encoder.fingerprint,encoder.dimensions):
                raise ValueError('Stored and query model identities differ')
            rows=connection.execute("SELECT chunk_id,source_id,source,page,text,metadata,vector_dims(embedding) FROM ingestion_chunks WHERE run_id=%s AND strategy='B'",(run_id,)).fetchall()
            if len(rows)!=len(chunks): raise ValueError('DB/corpus size mismatch')
            for cid,source_id,source,page,text,metadata,dim in rows:
                c=self.chunks.get(cid)
                if c is None or (source_id,source,page,text,metadata,dim)!=(c['source_id'],c['source'],c['page'],c['text'],c['metadata'],384):
                    raise ValueError('DB/corpus identity mismatch')

    def connect(self):
        import psycopg
        connection=psycopg.connect(self.url,connect_timeout=5,options='-c default_transaction_read_only=on')
        row=connection.execute("SELECT current_database(),current_setting('transaction_read_only')").fetchone()
        if row!=('day6_lab','on'):
            connection.close();raise ValueError('Expected day6_lab read-only transaction')
        return connection

    def search(self, query, top_k=3):
        check_k(top_k)
        vector=self.encoder.embed_query(query)
        if len(vector)!=384 or not all(math.isfinite(v) for v in vector) or not 0.99<=sum(v*v for v in vector)**0.5<=1.01:
            raise ValueError('Invalid query vector')
        with self.connect() as connection:
            rows=connection.execute("""SELECT chunk_id,1-(embedding <=> %s::vector) AS score
                FROM ingestion_chunks WHERE run_id=%s AND strategy='B'
                ORDER BY score DESC,chunk_id LIMIT %s""",(json.dumps(vector),self.run_id,top_k)).fetchall()
        return [{**self.chunks[cid],'score':float(score),'strategy':'dense'} for cid,score in rows]

    def snapshot(self):
        with self.connect() as connection:
            rows=connection.execute('SELECT run_id,strategy,chunk_id,md5(row_to_json(t)::text) FROM ingestion_chunks t ORDER BY 1,2,3').fetchall()
            runs=connection.execute('SELECT run_id,md5(row_to_json(t)::text) FROM ingestion_runs t ORDER BY 1').fetchall()
        return hashlib.sha256(json.dumps([rows,runs]).encode()).hexdigest()
