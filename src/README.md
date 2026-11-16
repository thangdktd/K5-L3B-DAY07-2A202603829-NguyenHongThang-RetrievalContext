# Code

Đặt code của bạn tại đây hoặc mở rộng [starter](../starter/README.md). Khung agent chưa kết nối model và vector store thật.

## Checkpoint 3A: local DEV retrieval

`build_final_benchmark.py` is the sole official benchmark generator.
`benchmark_control.py` validates, audits and controls freeze/rebuild. See
`../data/README.md` for schema v2 and immutable freeze semantics.

`retrievers.py` implements BM25, local query embeddings, read-only Day 06
pgvector Dense, and Hybrid RRF. `evaluate_retrieval.py` reuses the starter context
packer and group evaluator, filters to DEV before retrieval, and has no TEST or
Agent mode. No gold, expected answer, or absence annotation enters retrieval.

Tested environment: Windows, Python 3.13; use the existing Day 07 `.venv`.
Dependencies are in `requirements.txt`. Day 06 supplies its existing local
`models/all-MiniLM-L6-v2` and `starter/.env` DATABASE_URL (never logged). The model
runs offline on CPU; its fingerprint and dimensions must match the stored run.
Connections permit loopback only and enforce read-only `day6_lab` transactions.
No Day 06 Python module is imported or executed; no Day 06 pycache is created.

From the repository root:

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe -X utf8 src/build_final_benchmark.py --check
.venv/Scripts/python.exe -X utf8 src/evaluate_retrieval.py --output report/individual/checkpoint3a-recheck
```

Use a fresh output directory on each run. The runner refuses to overwrite an
existing output directory. Metrics and full per-query traces are saved there.
Initial results and error analysis: `../report/individual/checkpoint3a/`.
The baseline-only run uses `starter/baseline.py --split dev`; the runner compares
TF-IDF, Dense, BM25, and Hybrid at both 800 and 2400 character budgets.

Comparison conditions: same frozen 292 strategy B chunks, 15 answerable DEV
queries, raw query text, no metadata filters, top-3. BM25 k1=1.5/b=0.75; RRF takes
20 candidates from each branch with k=60 and deterministic ID ties. Dense uses
exact cosine ranking. Query vectors are cached and reused; initial encoding time
is separate from warm retrieval/context latency. Costs are external service
charges only (zero); local compute/memory costs are not monetized.

The provisional choice is Hybrid RRF with 2400 characters based on DEV evidence
coverage; this is not a final Agent or TEST configuration. Stop at 3A until user
approval for 3B. TEST and LLM Agent have not been run.

## Checkpoint 3B: OpenAI Agent (DEV only)

`openai_agent.py` implements a `Controller.decide(question, history)` adapter and
an extended starter-style loop with explicit abstention and error outcomes.
The frozen benchmark, its evaluator, and starter/agentic.py are unchanged by 3B.
The extension preserves the starter search/answer interface and adds abstain;
it uses the 3A Retriever.search(query, top_k) interface with no metadata filters.

Install the official `openai` SDK from `requirements.txt` into the Day 07 venv.
Set `OPENAI_API_KEY` in the process environment or copy `.env.example` to `.env`
in the Day 07 root and edit the key locally. Do not send keys in chat or logs.
`.gitignore` excludes `.env` and `.env.*` except the key-free `.env.example`.
The client uses the official https://api.openai.com/v1 endpoint, disables automatic
retries and does not inherit a custom API base URL. No Gemini integration is used.

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe -X utf8 src/build_final_benchmark.py --check
.venv/Scripts/python.exe -X utf8 src/run_agent_dev.py --output report/individual/checkpoint3b
```

The default model is gpt-4.1-mini; actual response model IDs are logged. Model
access is not assumed; a provider error stops the DEV run and is recorded as
error, never as abstention. No fallback model or automatic retry occurs.
A fresh output directory is required. The CLI has no TEST option.

Controller behavior: real Responses API strict function calling with search and
finish tools; force initial search, permit focused follow-ups, then force finish
after 3 searches. Up to 4 provider calls per case; temperature 0 and max 900 output
tokens per call. Tool outputs carry only the latest bounded cumulative context;
old context is not retained in the provider conversation. Corpus text is treated
as untrusted data. Only question strings enter the Agent; labels, gold, expected
answers and absence reasons are excluded.

Context: 2400 characters including compact chunk_id/source_id/page headers;
deduplicate by chunk_id; newest search results first so supplemental retrieval
can replace obsolete context. Full chunks only; chunks that do not fit are
skipped. This is a documented change from 3A's source-file headers and append-only
packing and must be evaluated from the actual 3B traces. No gold-informed packing
or special-case benchmark question ID handling is used. The prompt requires all
requested facts/comparison sides; q12 completeness is checked with the frozen
AND/OR evaluator after the run, never inside retrieval or model prompts.

`traces.json` records calls, function arguments, search results, contexts, answers,
citations, errors, latency, requested/actual models and usage. `runtime.json`
records config, total usage, stop reason/completeness and before/after database
hashes. Errors log only exception class/status/request ID, not provider bodies,
headers, exception strings or keys. Output exists even after a provider error;
remaining cases are explicitly listed as not run. No fake traces are substituted.

After a complete real run, copy `reviews_template.json` to `reviews.json` and
review every answer against actual cited context. Fill answer_grade 0-2,
citation_support booleans and abstention_correct, with a reason for each case.
A reviewer must inspect q12 Mode 1 AND Mode 2, correct model/table scope and units;
valid IDs or a verifier model alone do not prove grounding. Aggregate with:

```powershell
.venv/Scripts/python.exe -X utf8 src/evaluate_agent_dev.py --run report/individual/checkpoint3b --reviews report/individual/checkpoint3b/reviews.json
```

The official starter aggregator rejects missing/null labels. Reports should
identify who performed review; assistant review is not independent human grading.
Use actual token usage and verified actual-model prices for cost estimates; usage
missing from provider responses is marked unknown. No TEST, commit/push or
Checkpoint 4 is authorized here.

Official references checked 2026-11-16:
- https://developers.openai.com/api/docs/guides/function-calling
- https://developers.openai.com/api/docs/models/gpt-4.1-mini
- https://developers.openai.com/api/docs/quickstart

### Structured per-claim citations (offline repair after q12)

The current `finish` schema is `{status, claims: [{text, chunk_ids}]}`. The model
chooses IDs for each claim; text must be a short verbatim supported clause from
CURRENT context. The application validates every pair, then renders each claim
followed by its selected `[chunk-id]` and deduplicates the final `citations` array
in first-use order. It does not add, replace, or infer a missing source. Any
unsupported claim rejects the whole answer; abstain remains abstain.

Final trace/output still has `answer` and `citations`, preserving the starter
output contract and official evaluator. The old finish argument format is only
accepted by the local decoder for existing adapters/recordings, with the existing
strict inline validator; it is not advertised in the model tool schema.
Completeness of all requested facts still requires post-run evaluation: neither
ID validity nor extractive matching can detect every silent omission or scope
error without semantic review. No benchmark gold enters inference. This repair
has only been tested with mocks; any real q12 confirmation needs user approval.

### Bounded deterministic grounding rules

`grounding.py` now separates content checks from citation formatting/membership
(`validate_citation_format`). The claims schema, model prompt, frozen evaluator
and gold remain unchanged. Unicode/spacing/punctuation normalization, a reviewed
unit-alias/contraction table, and ordered conjunction of adjacent affirmative
unguarded sentences are supported. Acceptance requires exact canonical token
sequence equality or an exact excerpt that preserves protected facts. Numeric
values/signs, SI prefix case, units, comparisons, conditions, negation, modality
and bound/uncertainty qualifiers are retained. No similarity threshold or arbitrary
synonym matching is used; unknown paraphrases fail closed.

Answer/error events contain `grounding_checks` with a per-claim/chunk proof method
or reason. A generic outer unsupported_cited_claim still preserves compatibility.
This cannot verify arbitrary semantic equivalence, table scope, exceptions in
other sentences or complete question coverage. Causal rewrites such as
"A, allowing B" from "A. B is possible" remain unverified. Do not expect the old
q12 claims to automatically pass. Actual new Agent runs still need approval.
