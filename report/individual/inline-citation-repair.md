# Checkpoint 3B — inline citation repair (offline only)

## Root cause supported by the q01 trace

The prior real finish call returned the correct factual answer and a valid
citations array, but answer contained no [chunk-id]. The existing validator
correctly rejected it. The system prompt already requested inline citations,
but the finish schema described answer only as a string and citations only as
an array of strings, without field-level linkage, format guidance or support
requirements. Strict function calling checked JSON structure, not adherence to
the natural-language inline requirement. This is observed model instruction
noncompliance enabled by underspecified schema, not retrieval or API failure.
No live run of the repair has occurred and prompt changes cannot guarantee future
model compliance. Existing traces and final q01 abstention are preserved.

## Changes

src/openai_agent.py:
- Strengthened system prompt and finish tool/field descriptions. Each supported
  clause must immediately precede its exact [chunk-id]; separate claims should
  have separate citations, preferably one claim per line. citations is still a
  list and must equal the distinct inline IDs. A placeholder example conveys
  format only and is not evidence or a benchmark answer.
- Kept the finish fields status/answer/citations; added a lowercase 64-hex ID
  pattern matching actual corpus IDs. No gold, expected answer or special
  benchmark ID handling was introduced.
- Added validate_cited_answer. It rejects missing/malformed/out-of-context IDs,
  mismatched inline/list sets, uncited trailing claims and unsupported adjacent
  claims. It never changes answer or inserts citations, and cannot promote
  explicit abstention to answered.
- Added a conservative extractive support policy: model must copy a short
  supporting clause verbatim from CURRENT context. Each adjacent claim must
  occur as a contiguous NFC/whitespace-normalized span in every cited chunk.
  Token boundaries prevent 6 hours from matching 36 hours or -6 hours.
  Unsupported claims fail with unsupported_cited_claim; format/membership failures
  retain invalid_or_missing_citations.

This support check is intentionally stricter than general paraphrase entailment:
it can reject correct paraphrases. Literal span support is necessary here but
not a complete semantic/conditions/table-scope judge; full benchmark evaluation
and direct review of source scope remain necessary. It does not prove that every
requested fact was answered. Source wording can also require surrounding context.
No claim of guaranteed semantic grounding is made from ID membership or mocks.
The conservative restriction was chosen to avoid accepting arbitrary IDs as proof
without an extra LLM call or benchmark gold access.

The existing starter evaluator, starter Agent example, retrieval and frozen
benchmark were not modified. No change to API model, retry, timeout or output
limits was made in this task. More extractive wording may affect future Agent
quality/token use; that must be measured in a separately approved run.

## Tests and verification

54/54 full unit tests PASS offline. New tests/test_inline_citations.py contains
nine mock tests covering all requested cases:
- Supported inline citation passes unchanged.
- Array without inline citation fails; no citation is silently appended.
- Citation outside CURRENT context fails.
- Whitespace/parenthesis/short/uppercase/nested bracket formats fail.
- Multiple correctly paired claims pass; swapped citations, uncited or invented
  claims fail.
- Abstention remains abstention even when a fake model adds a citation.
- A real context ID for an irrelevant chunk fails support checking.
- Numeric token/sign boundaries reject false substring matches.
- Unused array entries or unlisted inline citations fail synchronization.

Existing controller/function-call, provider-error, timeout, evidence-group and
retriever tests remain passing. All new model outputs are mocks, not actual DEV
results. Frozen generator rebuild and SHA-256 checks pass; no benchmark/evaluator
bytes changed. No live API, DEV/TEST evaluation, Day 06 edit, commit or push.

Files changed/created in this task:
- Modified src/openai_agent.py
- Created tests/test_inline_citations.py
- Created report/individual/inline-citation-repair.md

## Next step — approval required, not executed

A new q01-only real Agent session is recommended to check whether gpt-4.1-mini
actually follows the improved schema/prompt at the previously authorized small
token limits. That requires new user approval; offline mocks establish code
behavior only. Preserve old q01 results and save any approved new run to a new
output directory. Stop here; do not call the API or continue to other DEV cases.
