# Checkpoint 3A ? DEV retrieval, 2026-11-16

Completed benchmark repair, validation and freeze before implementing the three retrievers. No TEST retrieval, LLM Agent, commit or push. Day 06 was accessed read-only.

## Benchmark repair and freeze

q12 retains its question, expected answer and both original quotations. The schema now requires two groups with AND across groups and OR across alternatives inside a group. Hit@1 requires complete evidence in rank 1 alone; top-3 and context are scored over sets of chunks. Legacy single-group questions retain OR semantics. This follows the multi-evidence extension explicitly allowed in BENCHMARK.md and data/README.md. q12 is reported separately in metrics.json.

Baseline before repair (previous handoff): Hit@1 10/15, Evidence Hit@3 14/15, Context Evidence 7/15. Re-run after repair: 10/15, 13/15, 7/15. q12 was previously a false positive for top-3 completeness. Gold was not shortened or changed to improve retrieval.

Validation: 292 unique strategy B chunks, 20 unique answerable questions, 24 unique cases (17 DEV, 7 TEST); all source/page/evidence references resolve. Chunk metadata and content SHA-256 checked. t03/t04/t05 resolve to their declared physical pages and sections (21/14.3.4, 30/15.5, 35/16.1.8). The source corpus is the unchanged Day 06 export.

`data/benchmark_manifest.json` freezes schema day07-evidence-groups-v2 at 2026-11-16T10:55:58.300180+07:00. It contains hashes for corpus, raw question snapshot, benchmark, validation, absence audit, generator, evaluator and scoring documentation. The official generator uses the preserved raw Day 06 questions and corpus; legacy script entry points are retired. `--check` rebuilds in memory and verifies bytes and hashes. Rebuild and hashes passed after evaluation. No frozen file has been changed.

Unanswerable checking scans all 292 extracted chunks with boundary-aware terms, saves related chunk text/IDs/pages, and records review conclusions in data/unanswerable_audit.json. R410A-only guidance supports rejecting an unsupported R32 procedure; sound/noise descriptions are qualitative rather than the requested model rating; oil mentions do not specify the requested oil grade; PCB/inverter mentions do not provide IGBT specifications. Keyword absence is not proof of semantic absence; extraction/visual omissions remain a limitation. Unsupported claims about proprietary/internal manuals were removed before freeze.

## DEV comparison

Common conditions: original queries; no filters; same 292 chunks and 15 answerable DEV questions; unanswerable cases excluded from metric denominators. Dense uses the original all-MiniLM-L6-v2 (384 dimensions) fingerprint and exact pgvector cosine search on the B run. BM25 k1=1.5/b=0.75. RRF k=60, 20 candidates per branch. Top-3 ranks are scored identically.

| Method | Budget (chars) | Hit@1 | Evidence Hit@3 | Context Evidence | Median ms | Avg context chars |
|---|---:|---:|---:|---:|---:|---:|
| tfidf | 800 | 10/15 (66.7%) | 13/15 (86.7%) | 7/15 (46.7%) | 3.45 | 631.3 |
| dense | 800 | 12/15 (80.0%) | 13/15 (86.7%) | 7/15 (46.7%) | 42.32 | 612.5 |
| bm25 | 800 | 12/15 (80.0%) | 14/15 (93.3%) | 6/15 (40.0%) | 5.46 | 536.1 |
| hybrid_rrf | 800 | 11/15 (73.3%) | 15/15 (100.0%) | 7/15 (46.7%) | 44.52 | 569.1 |
| tfidf | 2400 | 10/15 (66.7%) | 13/15 (86.7%) | 13/15 (86.7%) | 2.39 | 1750.7 |
| dense | 2400 | 12/15 (80.0%) | 13/15 (86.7%) | 13/15 (86.7%) | 38.07 | 1803.3 |
| bm25 | 2400 | 12/15 (80.0%) | 14/15 (93.3%) | 14/15 (93.3%) | 3.41 | 1880.5 |
| hybrid_rrf | 2400 | 11/15 (73.3%) | 15/15 (100.0%) | 15/15 (100.0%) | 57.32 | 1929.9 |

Initial setup/model loading: 27.99s; encoding 15 original DEV questions: 0.88s (included in setup). Search timings use warm embedding cache and include context packing but exclude evidence scoring. One local run, sequential methods; not a statistical latency benchmark. External service cost: $0, no LLM token usage; local compute costs are not monetized.

For the 14 single-group questions, Hybrid at budget 2400 has Hit@1 11/14, Hit@3 14/14, Context Evidence 14/14. For q12 alone it has 0/1, 1/1, 1/1. No current stored chunk contains both q12 groups, so strict Hit@1 is structurally impossible for that question. This makes partial-evidence success distinguishable from complete coverage.

## Errors, hypotheses and measured changes

1. **q12 ? incomplete evidence sets.** TF-IDF top-3 contains the Mode 1 quote but not the Mode 2 quote; Dense contains the Mode 2 quote but not Mode 1. BM25 and Hybrid return both chunks (`d8a756ee...`, `2bc3b70e...`) at ranks 2/3. Hybrid therefore changes q12 Hit@3 from TF-IDF/Dense FAIL to PASS without modifying gold. Its first chunk still addresses using Mode 2 rather than comparing both purposes, so Hit@1 remains FAIL. At 800 characters only the first irrelevant-to-gold chunk fits; at 2400 both required quotes fit and context becomes PASS.

2. **q05 (also q09/q13/q14/q15) ? budget rejects correct evidence.** q05 evidence chunk `c4111d24...` is rank 1 for all methods, yet its full source header plus content exceeds 800 characters. The packer skips it and may produce irrelevant or empty context. Raising only the budget to 2400 fixes q05 context for all methods. Overall Hybrid context changes from 7/15 to 15/15 with unchanged ranking. Larger context increases average characters from 569.1 to 1929.9; downstream model quality/cost has not been measured.

3. **q04 ? lexical heading and dense similarity miss the answer-bearing chunk.** TF-IDF/Dense top-3 favor related refrigerant piping sections; BM25 ranks the actual material-requirement chunk `c4111d24...` first. Hybrid brings it to rank 2 and changes Hit@3 from FAIL to PASS. Hybrid does not improve Hit@1 for this case. The 2400 budget is needed to retain the full evidence chunk in context.

4. **q02 ? BM25-only miss.** Repeated stop/power vocabulary favors related chunks instead of the exact minimum-delay instruction. Dense provides complementary evidence; Hybrid top-3 covers the registered quote. This explains why BM25 alone remains 14/15 while Hybrid reaches 15/15.

5. **q11 ? wrong table scope at rank 1.** All methods rank an example calculating combined REYQ30 fuse capacity above the single-unit REYQ10 table row (`99868527...`). The example includes REYQ10 ampacity but not the requested single-unit recommended fuse. The registered row is rank 2 for TF-IDF/BM25/Hybrid and rank 3 for Dense. Hit@1 fails; 2400-character context covers the registered row and nearby table header. A future context step could preserve adjacent table headers and prioritize scope, but no benchmark edits or 3B implementation were made.

## Provisional choice and limits

DEV criterion declared in the runner: Evidence Hit@3, then Context Evidence Rate, then Hit@1, then latency. Provisional retrieval choice: Hybrid RRF + 2400 characters. It improves coverage but is slower than BM25 and loses one Hit@1 compared with Dense/BM25. This is not a final Agent configuration or independent TEST result. The benchmark is small, shares one source document, and exact quotation matching can reject semantically equivalent evidence. Context scores do not establish answer correctness, citation grounding, abstention or visual table interpretation. No unanswerable Agent behavior was measured.

## Reproduction and artifacts

Run the commands in src/README.md. metrics.json includes parameters, subset metrics, timings, model/run identity and matching database snapshots; traces.json includes all 120 DEV traces (4 methods ? 2 budgets ? 15 questions), full ranked chunks, scores, metadata, per-group evidence flags and packed contexts. No TEST traces exist.

Unit tests: 32/32 PASS, including six requested evidence behaviors, legacy evidence compatibility, Windows UTF-8 reads, deterministic rebuild/hash tampering and refusal by frozen/retired writers, BM25 scores/ranking, RRF fusion and Dense query scope/vector validation. Actual local model + pgvector integration completed successfully. Database read-only transaction status was checked at every connection; hashes over both runs and chunk rows (including embeddings) match before/after.

Checkpoint 3B remains pending user confirmation.
