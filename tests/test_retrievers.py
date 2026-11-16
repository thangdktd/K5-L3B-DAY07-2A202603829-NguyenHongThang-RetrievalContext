import json
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from retrievers import BM25Retriever, HybridRRFRetriever, DenseRetriever

def c(cid,text,score=1):
    return dict(id=cid,text=text,score=score,source_id='doc',source='doc.pdf',page=1,metadata={})

class BM25Tests(unittest.TestCase):
    def test_known_score_and_ranking(self):
        index=BM25Retriever([c('a','valve valve'),c('b','other other')])
        row=index.search('VALVE')[0]
        self.assertEqual(row['id'],'a')
        self.assertAlmostEqual(row['score'],math.log(2)*2*2.5/(2+1.5))
        self.assertEqual(index.search('unknown'),[])
        self.assertEqual(index.search(''),[])
        self.assertEqual(index.search('valve valve'),index.search('valve'))

    def test_length_normalization_ties_and_validation(self):
        index=BM25Retriever([c('z','valve '+'other '*20),c('a','valve')])
        self.assertEqual(index.search('valve')[0]['id'],'a')
        ties=BM25Retriever([c('z','valve'),c('a','valve')])
        self.assertEqual([r['id'] for r in ties.search('valve')],['a','z'])
        with self.assertRaises(ValueError):index.search('q',0)
        with self.assertRaises(ValueError):BM25Retriever([],k1=0)

class Fixed:
    def __init__(self,rows):self.rows=rows;self.calls=[]
    def search(self,query,top_k):self.calls.append((query,top_k));return self.rows[:top_k]

class RRFTests(unittest.TestCase):
    def test_fusion_ranks_not_raw_scores(self):
        dense=Fixed([c('a','A',999),c('b','B',0.1)])
        lexical=Fixed([c('b','B',-100),c('a','A',-999)])
        rows=HybridRRFRetriever(dense,lexical,candidate_k=20).search('query')
        self.assertEqual([r['id'] for r in rows],['a','b'])
        self.assertAlmostEqual(rows[0]['score'],1/61+1/62)
        self.assertEqual(rows[0]['component_ranks'],{'dense':1,'bm25':2})
        self.assertEqual(dense.calls,[('query',20)])

    def test_duplicates_empty_stream_and_cutoff(self):
        rows=HybridRRFRetriever(Fixed([c('a','A'),c('a','A'),c('b','B')]),Fixed([])).search('q',1)
        self.assertEqual(len(rows),1)
        self.assertAlmostEqual(rows[0]['score'],1/61)
        self.assertEqual(HybridRRFRetriever(Fixed([]),Fixed([])).search('q'),[])
        with self.assertRaises(ValueError):HybridRRFRetriever(Fixed([]),Fixed([]),rrf_k=0)

class DenseTests(unittest.TestCase):
    def test_query_sql_run_scope_and_dimension_validation(self):
        calls=[]
        class Encoder:
            def embed_query(self,query):return [1.0]+[0.0]*383
        class Connection:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def execute(self,sql,params):calls.append((sql,params));return self
            def fetchall(self):return [('a',0.75)]
        dense=DenseRetriever.__new__(DenseRetriever)
        dense.encoder=Encoder();dense.run_id='run';dense.chunks={'a':c('a','A')}
        dense.connect=lambda:Connection()
        rows=dense.search('question',2)
        self.assertEqual(rows[0]['score'],0.75)
        self.assertEqual(calls[0][1][1:],('run',2))
        self.assertIn("strategy='B'",calls[0][0])
        self.assertIn('ORDER BY score DESC,chunk_id',calls[0][0])
        self.assertEqual(len(json.loads(calls[0][1][0])),384)
        dense.encoder.embed_query=lambda query:[0]*384
        with self.assertRaises(ValueError):dense.search('q')

    def test_remote_database_rejected_before_connection(self):
        for url in ['postgresql://host.invalid/day6_lab','host=127.0.0.1 hostaddr=10.0.0.1 dbname=day6_lab']:
            with self.assertRaises(ValueError):DenseRetriever(url,'run',None,[])

if __name__=='__main__':unittest.main()
