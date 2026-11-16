# Day 7 report - Nguyen Hong Thang - 2A202603829

## Data and benchmark

Corpus: Daikin VRV IV+ installation/operation manual, revision 2025.11, source_id `daikin_vrv_ivplus_4p546222_1e_2025_11`. 48 physical PDF pages; selected content pages 4-41 (38 pages), 292 configuration-B chunks inherited from Day 06. PDF SHA-256 `603c36bab2370f3ed5f8cbba07b848ccfde22856b8550349b34c08fd0cef5c6d`. Local lab use was confirmed by the learner; permission to redistribute full text publicly and grader access remain unconfirmed. This is not an open-license claim. Resolve permission before publishing chunks/traces or the PDF.

Embedding: `sentence-transformers/all-MiniLM-L6-v2`, dimension384, fingerprint `7a729edee62a3c201eda95b4160f1429c1616adfb827e03539a8c035b60266de`. Local PostgreSQL/pgvector database `day6_lab`, run `6bb5bbaae6bdc33389366d82272c71e10e29f07ed97a354d820799b60d0705d3`. Query embeddings use the exact local Day06 model; no corpus re-embedding. Read-only transactions and before/after DB snapshot hashes verify no writes. Day06 repository was not edited.

Frozen schema `day07-evidence-groups-v2`: 20 answerable questions (15 DEV/5 TEST) and 4 unanswerable (2 DEV/2 TEST); total17 DEV/7 TEST. Manifest `data/benchmark_manifest.json`, frozen at `2026-11-16T10:55:58.300180+07:00`, manifest SHA256 `6db1bd0ede4ee75cc54ae62fc9ae2b83b90907ceebd38b01b64b4630b75c1767`. Protected file hashes passed again after TEST. No benchmark/gold/evaluator changes during final evaluation.

Evidence is AND across required groups, OR within alternatives. Hit@1 requires all groups in top1, Hit@3 all groups across top3; CER requires all groups in final context, matching source_id/page/quote with frozen whitespace normalization. q12 requires Mode1 AND Mode2. Unanswerable cases are excluded from retrieval denominators. Corpus/trusted-page checks and reproducible lexical audit are in `data/unanswerable_audit.json`; keyword absence alone is not proof of global absence.

## Retrieval and experiments

Same corpus/index/gold/query set; original queries, top3, no metadata filters or reranker. BM25 k1=1.5,b=0.75. Hybrid combines dense/BM25 using RRF k=60 and20 candidates per branch. Improvement1: Hybrid800, hypothesized complementary lexical/semantic coverage. Improvement2: Hybrid2400, hypothesized more complete conditions and multi-chunk evidence. Dense and BM25 measured independently too. These are valid existing checkpoint3a results, reused without rerunning.

| Configuration | Budget chars | Hit@1 | Evidence Hit@3 | CER | Median retrieval ms |
|---|---:|---|---|---|---:|
| TF-IDF baseline | 800 | 10/15 (66.7%) | 13/15 (86.7%) | 7/15 (46.7%) | 3.45 |
| Dense pgvector | 800 | 12/15 (80.0%) | 13/15 (86.7%) | 7/15 (46.7%) | 42.32 |
| BM25 | 800 | 12/15 (80.0%) | 14/15 (93.3%) | 6/15 (40.0%) | 5.46 |
| Hybrid RRF, improvement1 | 800 | 11/15 (73.3%) | 15/15 (100%) | 7/15 (46.7%) | 44.52 |
| TF-IDF | 2400 | 10/15 (66.7%) | 13/15 (86.7%) | 13/15 (86.7%) | 2.39 |
| Dense pgvector | 2400 | 12/15 (80.0%) | 13/15 (86.7%) | 13/15 (86.7%) | 38.07 |
| BM25 | 2400 | 12/15 (80.0%) | 14/15 (93.3%) | 14/15 (93.3%) | 3.41 |
| Hybrid RRF, improvement2 | 2400 | 11/15 (73.3%) | 15/15 (100%) | 15/15 (100%) | 57.32 |

Retrieval latency is warm search+packing, excludes initial model load and cached query encoding; no LLM cost. Agent compact source headers differ from the checkpoint3a proxy. The following pipeline context is what the Agent actually received, including extra searches.

| Configuration/split | Original Hit@1 | Original Evidence Hit@3 | Final CER | Median Agent ms |
|---|---|---|---|---:|
| baseline/dev | 10/15 (66.7%) | 13/15 (86.7%) | 9/15 (60.0%) | 3143.9 |
| selected/dev | 11/15 (73.3%) | 15/15 (100.0%) | 15/15 (100.0%) | 3130.0 |
| baseline/test | 2/5 (40.0%) | 3/5 (60.0%) | 3/5 (60.0%) | 3633.0 |
| selected/test | 4/5 (80.0%) | 4/5 (80.0%) | 5/5 (100.0%) | 4086.3 |

First Agent query ranking is reported separately in metrics; its aggregate equals original-query totals in this run. Multi-search union is not misreported as a top3 ranking. TEST selected Hit@3 is4/5 but final CER5/5 after additional searches. Direct context grades0/1/2 on all5 answerable TEST: baseline2/0/3; selected0/0/5. Per-case reasons are in reviews.json. Baseline t02 retrieves the same warning under adjacent section11.5 rather than11.4; wording/source/page support matches the frozen evidence predicate, but section scope remains a caveat documented in review.

## Agent and evaluation

Official OpenAI SDK3.51.0, Responses API. Requested `gpt-4.1-mini`, actual returned `gpt-4.1-mini-2025-04-14`. Real strict function calls `search` and `finish`; finish schema `claims:[{text,chunk_ids}]`. The model selects IDs. Controller validates context membership and deterministic support before rendering inline citations and the citations array; no arbitrary citations added. Max3 searches, top_k3, temperature0, max_output_tokens600/request, timeout60s, SDK max_retries0. Wrapper permits one logged transient retry per request; none occurred.

Context deduplicates chunk_id and retains chunk_id/source_id/page. Character budgets include headers/separators; complete chunks that do not fit are skipped. Selected uses Hybrid2400, baseline TF-IDF800; all other code/model settings match. Agent comparisons change both retriever and budget; retrieval ablations support analysis but do not isolate their causal effects on answer quality.

Inference receives only question, search results and necessary tool history, never full corpus, benchmark, expected_answer or gold_groups. Gold is used only after inference. Documents are untrusted data, not instructions. Model abstention, validator refusal and provider errors remain distinct in traces. A rejected proposal does not become a successful answer during evaluation.

Runner saves every completed case atomically, uses exclusive started markers and version hashes, and resumes missing cases without replaying completed cases. All17 DEV cases were newly run per profile under one code snapshot; historical q01/q12 traces are not mixed into metrics. Final config was locked at `2026-11-16T05:39:40.159638+00:00`, before TEST start05:40:33UTC. Baseline and selected each ran the same7 TEST cases once, as BENCHMARK requires. No prompt/retriever/validator/config tuning after TEST.

Reviews are direct assistant examination of final outputs and sources, not an independent human review or extra LLM-judge API. Grounded answer0=wrong/missing/abstain,1=partial,2=complete. Every answerable abstention scores0 even when proposed claims are correct. Citation validity counts unique emitted IDs with membership AND content support; repeated inline occurrences share the same ID. A heading that matches text but does not support the requested scope is invalid. All labels/reasons and unchanged output/proposals are saved.

| Configuration/split | Tool use | Cases with 1/2/3 searches | Grounded 0/1/2; mean /2 | Valid citations | Answers with citation | Correct abstention | False abstention |
|---|---|---|---|---|---|---|---|
| baseline/dev | 17/17 (100.0%) | 10/2/5 | 9/0/6; 0.80 | 6/7 (85.7%) | 7/7 (100.0%) | 1/2 (50.0%) | 9/15 (60.0%) |
| selected/dev | 17/17 (100.0%) | 15/1/1 | 6/0/9; 1.20 | 10/10 (100.0%) | 9/9 (100.0%) | 2/2 (100.0%) | 6/15 (40.0%) |
| baseline/test | 7/7 (100.0%) | 2/0/5 | 4/0/1; 0.40 | 1/1 (100.0%) | 1/1 (100.0%) | 2/2 (100.0%) | 4/5 (80.0%) |
| selected/test | 7/7 (100.0%) | 4/0/3 | 3/0/2; 0.80 | 2/2 (100.0%) | 2/2 (100.0%) | 2/2 (100.0%) | 3/5 (60.0%) |

### Examples and error analysis

- Answerable q01 selected DEV: accepted answer with supported inline source, grounded2. Exact answer/citations/search calls in `dev/selected/cases/q01.json`.
- Multi-evidence q12 selected DEV: both Mode1/Mode2 retrieved; model-selected claim IDs are correct, but `unsupported_cited_claim` guard rejects. Final output abstains, grade0. Header numbers and sentence boundaries make bounded numeric/condition matching over-conservative. This is validator rejection, not retrieval failure.
- Unanswerable DEV R32 retrofit: selected performed extra search then rejected an R410A charging proposal that did not establish applicability to R32. Final refusal is correct. Baseline emitted only a charging heading: not a refusal, and citation does not support the requested R32 scope. Other unanswerable DEV (rated noise) is a model refusal after3 searches.
- DEV error1: baseline q05 context800 omitted the30mg/10m requirement; selected Hybrid2400 retained evidence and answered correctly. Pipeline CER improves9/15 to15/15, complete answers6/15 to9/15. This is a combined configuration effect.
- DEV error2: historic q12 lacked inline/multi-source citations; structured claims improved selected sources, but current guard still rejects correct content. Keep historical traces as development evidence, not a controlled metric comparison. q07,q08,q10,q11,q13 also have complete selected context but guard rejection. No further semantic-validator development was performed.
- DEV error3: baseline q11 mixed22A ampacity with80A fuse from another combined model, missing the required25A row. Hybrid retrieves the correct row but table-sensitive guard still rejects. Distinguish wrong table retrieval from correct-table false rejection.
- TEST selected t02/t04: complete context and supported proposals rejected by support guard. t05: legitimate setting `[2-49]` inside claim text triggers blanket bracket/citation-format guard, despite correct model-selected source and >50m/highest-outdoor conditions. Final abstain scores0; bug recorded, not fixed after TEST. Baseline t04/t05 truly lack required context; t03 has context but guard rejects. Both TEST unanswerables are actual model refusals after3 searches, not provider errors.

### Latency, cost and final selection

| Configuration/split | API requests | Input tokens | Output tokens | Provider latency sum s | Estimated USD |
|---|---:|---:|---:|---:|---:|
| baseline/dev | 46 | 36260 | 2072 | 57.537 | 0.0178192 |
| selected/dev | 37 | 36164 | 2563 | 61.326 | 0.0185664 |
| baseline/test | 24 | 19174 | 884 | 26.525 | 0.0090840 |
| selected/test | 20 | 21846 | 1052 | 26.726 | 0.0104216 |

New evaluation total:48 Agent sessions,127 API requests,113444 input +6571 output =120015 tokens; cached0;0 errors/retries. Summed provider latency172.114s. Wall time including setup: DEV144.230s + TEST76.156s =220.386s, excluding review/offline tests. Estimated cost $0.0558912 at input$0.40/M, output$1.60/M, cached input$0.10/M; [OpenAI pricing](https://developers.openai.com/api/docs/models/gpt-4.1-mini), checked2026-11-16. Estimate is not an invoice. Historical pilots/diagnostics are excluded; failed historic calls may lack usage.

Selected on DEV because complete context15/15, correct answers9/15 vs6/15, citations10/10 vs6/7, correct abstention2/2 vs1/2. DEV requests37 vs46, cost increase only$0.0007472; median around3.1s. Larger context costs more per call but reduces searches. TEST mean0.8/2 shows validation remains the main answer bottleneck despite CER100%. No configuration was selected again using TEST. Basic rubric has no absolute accuracy threshold; these results do not establish production readiness.

## Advanced challenge

Not attempted. No100-page bonus claim.

## Reproduction, submission artifacts and limitations

See `final-evaluation/REPRODUCE.md`. Working-tree content hashes in final_config_lock and source_snapshot are the code version; no fictitious commit is claimed. Python3.13.7; dependency pins in `src/requirements.txt`, observed packages in `environment_packages.json`. Never submit .env/API keys.

- Frozen data/evidence: `data/{chunks,questions,agent_cases,benchmark_manifest,benchmark_validation,unanswerable_audit}.json`; official builder `src/build_final_benchmark.py`, guard `src/benchmark_control.py`.
- Retrieval code/results: `src/retrievers.py`, `checkpoint3a/{metrics,traces,verification}.json`.
- Agent/runner/evaluation: `src/{openai_agent,run_agent_suite,evaluate_agent_suite}.py`, tests in `tests/`.
- Final evidence: `final-evaluation/{dev,test}/{baseline,selected}/cases/*.json`, `traces.json`, `reviews.json`, `metrics.json`, split `summary.json`.
- Protocol/version: `suite_manifest.json`, `final_config_lock.json`, `source_snapshot/`, `dev_decision.md`, TEST start/completion markers.
- Audit: `api_attempts.jsonl`, split `runtime.json`, `final_verification.json`, `final_unit_tests.log`, `submission_inventory.json`.

| Rubric | Evidence status | Remaining limit |
|---|---|---|
| Data/benchmark13 | PARTIAL | Counts/freeze/evidence pass; redistribution/grader access unconfirmed |
| Retrieval17 | PASS | Four real methods including Day06 pgvector; comparable DEV results |
| Agent/context17 | PASS | Real model/tools/logs/context/citations; high false abstention disclosed |
| Evaluation17 | PASS | Both profiles DEV/TEST with per-case labels; learner should verify assistant labels |
| Experiments13 | PASS | Two improvements, DEV errors, pre-TEST lock, measured cost/latency |
| Reproducibility/report8 | PARTIAL | Code/hash/commands present; local Day06 assets and grader access need arrangement |

PASS indicates supporting artifacts, not a guaranteed awarded score. Final offline tests83/83 PASS; benchmark/code/DEV hashes match; DB snapshot unchanged. No commit/push. Learner must resolve data sharing permissions and grant grader access before submission.
