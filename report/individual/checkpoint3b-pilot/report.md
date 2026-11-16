# Checkpoint 3B pilot — stopped on authentication error

Key presence check: PASS (value never printed). A nonempty key was loaded from
Day 07 environment/.env. Presence does not establish that OpenAI accepts the key.

Requested pilot: exactly three DEV cases, q01 (simple answerable), q12
(two required evidence groups), q_unans_dev_01 (unanswerable). No other DEV case
or TEST case was executed.

Configuration: requested model gpt-4.1-mini, official OpenAI SDK 3.51.0 Responses
API, max 3 searches, top-3 Hybrid RRF, context budget 2400 characters, temperature
0, max 600 output tokens per request (reduced from 900 for the pilot), automatic
provider retries disabled. Maximum 12 requests if all three cases had completed.

Observed result:

| Case | Status | API requests | Searches | Grounding/citation/abstention review |
|---|---|---:|---:|---|
| q01 | provider_error: AuthenticationError, HTTP 401 | 1 | 0 | Not assessable: no model output |
| q12 | Not run after error | 0 | 0 | Not assessed |
| q_unans_dev_01 | Not run after error | 0 | 0 | Not assessed |

Total: 1 attempted API request, 0 successful responses. Provider latency for the
failed request was about 7.99 seconds. No function call or corpus retrieval was
returned/executed; no answer or citations were produced. This is not abstention.

Provider input/output/cached token usage: NOT REPORTED. The trace's local usage
counters are zero because no successful usage object was received; they must not
be interpreted as measured billable token usage. API cost is unknown/null; no
invoice or billing endpoint was queried. No cost estimate is asserted.

The run stopped on the first provider error without retry or model fallback.
The error log contains only exception type, HTTP status and request ID, with no
provider body, headers, exception text or key. The response model/access therefore
remains unverified. Do not infer that the model is unavailable from a 401 error.

Verification: 41/41 unit tests PASS before the pilot. Benchmark frozen rebuild and
hash validation PASS after the pilot. The Day 06 database used read-only
transactions and its before/after row snapshots match. No Day 06 repository edit,
benchmark edit, TEST run, full DEV run, commit or push. No further API calls made.

Files changed for pilot support: src/openai_agent.py (configurable output-token
limit), src/run_agent_dev.py (--pilot fixed three-case selection and request
counts). Artifacts: runtime.json, traces.json, context_metrics.json and the empty
reviews_template.json. Empty review artifacts are not successful benchmark labels.

Next: correct or replace the OpenAI API credential locally in Day 07 .env and
request a pilot retry. Do not send the key in chat. If OPENAI_API_KEY is also set
in the process environment, it takes precedence over .env (override=False).
The pilot must remain three cases; do not continue to full DEV or Checkpoint 4.
