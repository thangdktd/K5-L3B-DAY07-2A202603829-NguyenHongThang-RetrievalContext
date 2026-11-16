# Checkpoint 3B — implementation ready; live DEV run pending credentials

Status on 2026-11-16: **incomplete — OPENAI_API_KEY is not configured**.
The real DEV runner was invoked and stopped at credential preflight before any
API request, local model load, database connection, or output-directory creation.
This is a configuration blocker, not provider abstention or a benchmark failure.

Implemented:
- Official OpenAI Python SDK 3.51.0 installed in the independent Day 07 venv.
- Responses API strict function-calling controller (`search`, `finish`), default
  requested model gpt-4.1-mini; actual model/access not yet verified.
- Hybrid RRF integration with the existing read-only Dense/BM25 retrievers.
- Maximum three searches and four model calls per case; initial search forced,
  supplementary queries allowed; final decision forced after the search limit.
- 2400-character context, chunk-ID deduplication and source_id/page/chunk_id
  headers. New results take priority so follow-up searches can update context.
- Only question strings go to the Agent; no gold, expected answers, answerable
  labels, absence reasons or benchmark IDs enter model requests.
- Citation membership/inline validation and explicit abstention. Completeness and
  semantic support still require direct review; the prompt requires all facts and
  comparison sides, and the frozen group evaluator checks q12 context after a run.
- Sanitized provider/retrieval/protocol errors separated from abstention; no retry
  or silent model fallback. SDK debug logging suppressed; provider bodies, keys,
  headers and exception strings are not logged.
- Per-case traces, model/function calls, queries, retrieved chunks, final context,
  usage, latency and database snapshots are implemented. Cost is estimated only
  from reported usage and verified actual-model rates, otherwise left unknown.
- DEV-only review/aggregation command reuses starter/agent_metrics.py and rejects
  incomplete labels. Grounding must be reviewed against actual cited text.

Validation: **41/41 unit tests PASS**. All OpenAI tests use mocked responses and
make no paid requests. They cover protocol matching, follow-up search, bounded
context, deduplication, citation rejection, three-search limit, abstention,
provider/retrieval errors, malformed responses and official endpoint selection.
The frozen benchmark rebuild/SHA-256 check passes. `.env`, `.env.local` and
`starter/.env` are confirmed ignored by Git; `.env.example` contains no key.

New files:
- .env.example
- src/openai_agent.py
- src/run_agent_dev.py
- src/evaluate_agent_dev.py
- tests/test_openai_agent.py
- report/individual/checkpoint3b-status.md

Updated files: src/README.md and src/requirements.txt.
No 3B changes to the frozen benchmark, starter evaluator, 3A results or Day 06.
No TEST execution, commit, push or Checkpoint 4 work.

Actual DEV Agent metrics: **not measured**. Actual model ID, grounded answer,
citation validity, tool use, abstention, false abstention and latency are pending.
No real answerable/unanswerable trace exists yet; mock tests are not substituted.
OpenAI requests sent: **0**; actual generated input/output tokens: **0**; API
request charges incurred by this run: **0**. No claim is made about account billing.

Next required action: configure OPENAI_API_KEY locally in the Day 07 root .env
or process environment (never send it in chat), then resume the already-authorized
DEV run, inspect all 17 cases including q12 and the two unanswerable cases, fill
review labels/rationales, aggregate metrics and save two real trace examples.
See src/README.md for exact commands. Remain at Checkpoint 3B.

Documentation checked:
- https://developers.openai.com/api/docs/guides/function-calling
- https://developers.openai.com/api/docs/models/gpt-4.1-mini
- https://developers.openai.com/api/docs/quickstart

The model page currently marks gpt-4.1-mini deprecated while listing function
calling support. Keep the user's requested default; if the account rejects it,
stop and report rather than silently choosing a different provider/model.
