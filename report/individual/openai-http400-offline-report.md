# Day 07 — HTTP 400 offline diagnosis and logging repair

No OpenAI API requests were made in this step. Documentation was read through the
web tool; all SDK requests in unit tests used in-memory MockTransport, no sockets.
No Agent benchmark or TEST split was executed. Existing mock Agent unit tests
are behavioral tests, not paid/live Agent runs.

## Actual API and parameter compatibility

Installed official SDK: openai 3.51.0. Diagnostic calls client.responses.create,
POST https://api.openai.com/v1/responses. It is Responses API, not Chat Completions.
The previous captured payload was exactly model=gpt-4.1-mini, input=Reply OK,
max_output_tokens=10, store=false. Timeout 20 seconds and max_retries=0 configure
the client, not the JSON body. There were no tools, tool_choice or temperature
parameters in the minimal diagnostic request.

| Field | Responses | Chat Completions | Observed code |
|---|---|---|---|
| Input | input | messages | input, correct for Responses |
| Output cap | max_output_tokens | max_completion_tokens | correct name, invalid old value 10 |
| temperature | supported range 0..2 | supported range 0..2 (model-dependent) | omitted in diagnostic; Agent uses 0 |
| tools | function fields type/name/parameters/strict at top level | function definition nested under function | Agent uses Responses shape |
| tool_choice | required/auto/none or {type:function,name:...} | required/auto/none or nested function selector | Agent uses Responses shape |

The gpt-4.1-mini model documentation lists Responses and Chat Completions,
function calling and structured outputs as supported. Deprecated status alone
is not proof of account access or a cause of the recorded HTTP 400. The model
was not changed.

## Definite code defect versus historical inference

Official Responses create reference explicitly specifies minimum 16 for
max_output_tokens. Therefore the old value 10 violates the documented constraint.
This is a concrete code/configuration defect and a likely explanation of HTTP
400. The old error body/message was not preserved, so its exact returned
error.code/type/param cannot be reconstructed or asserted. No historical log
was edited to invent those fields. No evidence of mixed APIs was found.

Prepared fix: src/diagnose_openai.py now uses MAX_OUTPUT_TOKENS=16, the documented
minimum. Input Reply OK, endpoint/model, timeout20 and retries0 remain the same.
This configuration has only been exercised through mock transport. The original
single-request marker still prevents resubmitting to its existing output path;
a future approved run must use an explicitly selected fresh output file.

## Logging repair

Added filtered_error, handling SDK BadRequestError as well as other exceptions.
It records status_code and nested error.code/type/param/message. Known error codes,
types and request parameter names are allowlisted; unknown or secret-containing
metadata is replaced with [filtered]. The message is a generated safe summary,
optionally retaining a numeric minimum for max_output_tokens. It is NOT the raw
provider message. Arbitrary body/message strings can echo credentials, headers,
prompts, account details or URLs, so they are intentionally omitted. The exact
configured key is also supplied to the metadata filter.

No str(exception), raw error body, request/response object or header collection
is logged. Existing transport events keep only phase names, times and exception
class. Timeout continues to be recorded as an error, with no invented usage and
no automatic retry or model fallback. This diagnostic logging change is isolated:
Agent error behavior, retrieval, Day 06 and the frozen benchmark were not modified.

## Tests

45/45 complete unit tests PASS. Four new tests in tests/test_diagnose_openai.py:
1. A real SDK BadRequestError from mocked HTTP 400 preserves safe structured
   fields/minimum while discarding a fake API key, Authorization text, sensitive
   prompt text and unknown body fields; verifies Responses route/payload16.
2. A mocked transport ReadTimeout becomes APITimeoutError, submits once and logs
   no sensitive exception text; usage/status remain unavailable.
3. Nested error objects and unknown metadata are filtered conservatively.
4. Existing output file stops execution before client construction.

Mock validation body/minimum16 is synthetic test data, NOT a recovered response
from the prior real request. No live success or real server error fields are
claimed from mocks. Frozen rebuild/hash validation passes after changes.

## Files and next step

Modified: src/diagnose_openai.py.
Created: tests/test_diagnose_openai.py, this report.
No benchmark/Day06/retrieval changes, TEST execution, commit or push.

A further single live request with max_output_tokens=16 is needed to establish
whether the corrected minimal request succeeds and to obtain real usage/model
or safe server error fields. It is not needed to identify the documented invalid
value10. That request is NOT authorized/executed in this step. Stop awaiting user
approval. Do not run a pilot Agent as part of such a diagnostic request.

Official sources inspected 2026-11-16:
- Responses create (max_output_tokens minimum16):
  https://developers.openai.com/api/reference/resources/responses/methods/create
- Chat Completions create:
  https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create
- Function-calling schemas:
  https://developers.openai.com/api/docs/guides/function-calling
- Model support:
  https://developers.openai.com/api/docs/models/gpt-4.1-mini
