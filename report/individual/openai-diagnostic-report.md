# OpenAI timeout diagnosis ? one request only

## Offline findings (zero API requests)

Day 07 .env key exists; value and headers were never displayed. No conflicting
API base URL or proxy environment variables were configured. Windows explicit
proxy and AutoConfigURL/PAC settings were absent/disabled. This does not exclude
transparent network interception, VPNs, security software or upstream firewalls.

The existing Agent uses OpenAI SDK 3.51.0 / httpx2, endpoint
https://api.openai.com/v1/responses, max_retries=0, configured SDK timeout=45.0,
effective HTTP timeout Timeout(timeout=45.0), trust_env=True. The 42.49-second
trace is elapsed wall time until an APITimeoutError, not evidence of a configured
42.49-second deadline. HTTP timeouts apply to transport phases; scalar timeout is
not necessarily a strict total wall-clock deadline. The SDK wraps underlying
transport timeout errors as APITimeoutError. The old log discarded that exception
chain and transport stage, so its exact failing TCP/TLS/read phase is unknown.

The old failure occurred inside client.responses.create before any retrieval:
zero searches, empty context, no response/status/request ID. No evidence of
retry, retrieval/database blocking or Agent looping.

Actual SDK payload serialization was inspected offline with MockTransport (no
sockets): initial request about 2371 bytes with one user input item; synthetic
follow-up with full 2400-character context about 5234 bytes and three input items
(user question + latest function call + latest function output). These measured
sizes use JSON reserialization for audit, not a captured historical wire body.
Initial instructions are 1279 characters and two function schemas are attached.
No corpus/benchmark/gold/expected_answer container is included. Code only sends
question text and the latest bounded context, with at most three search queries;
old response text/context does not accumulate. Follow-up character count is not
an exact token bound, and model-generated queries remain variable length.

See openai-offline-audit.json. Its two transport calls are mocks, not API calls.

## Exactly one real diagnostic request

Standalone script: src/diagnose_openai.py. No retrieval, Agent, database access or
model-list/credential-test calls. Input exactly Reply OK, requested model
gpt-4.1-mini, max_output_tokens=10, timeout=20 seconds, max_retries=0,
store=False, follow_redirects=False. A persistent marker prevents accidental
resubmission using the same output path; an HTTP request hook caps sends at one.
No function schemas or corpus included; actual payload size 80 bytes.

Result: HTTP 400 BadRequestError after 7102.333 ms. One attempted request, one
HTTP error response, zero successful generation responses. Actual response model,
reply text and input/output token usage are unavailable. API cost is unknown/null;
no zero-billing assertion or estimated cost is made without usage data.

Transport evidence: TCP connect completed (~3.73 seconds); TLS completed
(~0.56 seconds); headers/body sent; response headers received after ~2.53 seconds
of waiting; response body read. No transport failure or timeout occurred in this
request. Trace timestamps include client initialization; reported latency starts
immediately before the SDK request.

The sanitized log retains only status, exception types and request ID. It did not
retain the server error message/code/param, so the exact reason for HTTP 400 is
NOT established. In particular, a rejection of max_output_tokens=10 is only a
possible explanation, not a verified diagnosis. No second request was sent with
a changed token cap/model. A 400 also does not establish generation permission,
model availability or completion of key validation.

## Conclusion and next actions (not executed)

Current evidence excludes a persistent inability to establish TCP/TLS/HTTP on the
observed route and excludes oversized corpus/history as the cause of the first
Agent request. SDK can send and receive HTTP using this environment. The earlier
timeout may have been transient network/upstream/API latency; the old trace lacks
transport details to distinguish them. The minimal request instead exposes an
API request-validation error (400), with exact rejected field unknown.

For any future explicitly approved request, first add allowlisted error.code,
error.type and error.param logging (no raw error message/body, key or headers).
Verify request limits against official documentation before changing parameters.
Keep retries disabled and a one-request cap; only after resolving 400 should a
new Agent pilot be considered. No timeout increase, model switch, direct/proxy
route switch or retry was performed here.

Frozen benchmark hash verification passes. No TEST, full DEV, pilot Agent,
Day 06 mutation, commit or push. Stop after this single diagnostic request.
