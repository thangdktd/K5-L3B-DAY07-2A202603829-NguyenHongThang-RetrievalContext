# q12 multi-source citation repair — offline only

Cause: the prior q12 call produced one prose answer and a separate flat citations
array. Despite prompt instructions, it omitted inline citations and omitted the
Mode1 source from that array. Both evidence groups were in context, so retrieval
and budget were not the failure. Strict JSON schema did not bind individual
claims to sources. Old real-run artifacts remain unchanged.

Solution: finish now exposes only `{status, claims:[{text,chunk_ids}]}`. Each model
claim selects its own source IDs. Atomic claims and short source excerpts are
requested; separate facts from separate chunks into separate claims. For abstain,
use claims=[]; do not present a partial comparison as a full answer.

Controller decodes this to an internal claims action. The application checks all
IDs against CURRENT context and verifies contiguous NFC/whitespace-normalized
extractive support for each claim in every selected source. Only after all claims
pass does it render `text [chunk-id]` per line and derive a deduplicated citations
list from those model-selected IDs, preserving first-use order. It never guesses,
adds, substitutes or looks up an alternative source for a failing claim. Missing
source, wrong ID or missing support rejects the whole proposed answer; no partial
answer is silently promoted. Explicit abstention stays abstention.

Compatibility: GUIDE.md permits replacing/extending the Agent architecture. Final
answer/citations/status output and trace IDs remain compatible with the starter
and rubric. The frozen evaluator and benchmark are unchanged. A read-only legacy
finish decoder remains for prior adapters/recordings; legacy answers still need
correct inline citations and support. The new model schema does not offer the
legacy shape or an automatically repaired fallback.

Limits: exact source excerpts can reject valid paraphrases; this policy is
retained from the prior support validator, not loosened here. Matching excerpt
text is not a complete scope/semantic-entailment or question-completeness judge.
If the model silently omits an entire requested fact, the renderer cannot infer
that omission from gold (gold is deliberately unavailable). Post-run AND/OR gold
coverage and direct answer review remain necessary. No universal grounding or
multi-evidence completeness guarantee is claimed from mock tests.

Tests: 64/64 full unit tests PASS offline. Ten new structured-claim tests cover
two claims/two chunks, missing one context source, empty chunk_ids, wrong/swapped
or malformed IDs, absent support, per-claim support with multiple selected sources,
array deduplication, malformed objects, schema shape and abstention preservation.
The 54 prior tests still pass, including strict legacy inline validation. No
OpenAI API, live DEV/TEST or real retrieval run was performed.

Token/schema effect (offline character counts, not tokenizer measurements):
- System prompt: 1982 -> 1753 characters.
- Compact finish schema JSON: 947 -> 884 characters.
- Equivalent synthetic valid two-claim output: 348 -> 249 characters; model no
  longer repeats every ID in both prose and a separate flat citations array.
- Nested claim keys add overhead, but one ID per claim is generated once. Final
  rendered answer plus deduplicated citations is generated locally at no provider
  token cost. Actual input/output tokens and behavior under max250 output tokens
  remain unmeasured until a separately approved q12 run. No API limits changed.

Files: modified src/openai_agent.py and src/README.md; added
tests/test_structured_claims.py, structured-citation-offline-metrics.json and this
report. scratch/citation_schema_before.json records pre-edit offline character
counts. Retrieval, Day06, benchmark and evaluator unchanged. Frozen rebuild/hashes
PASS. No commit/push. Stop awaiting approval before running q12 again.
