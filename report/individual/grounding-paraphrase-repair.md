# Grounding validator — bounded paraphrases, offline repair

Root cause: the prior q12 validator required the entire normalized claim to be
one contiguous substring of each cited chunk (`re.search(re.escape(claim),
chunk_text)`). Mode1 joined two sentences with "and" and Mode2 rewrote "Consulting
... and changing ... is possible" using "allowing ...". These are not literal
contiguous substrings. Citation IDs/schema were valid; content matching failed.
Old traces/labels are preserved; no real run or new benchmark scoring was done.

## Changes

- New src/grounding.py: pure deterministic rules, no model, retriever, benchmark
  imports or question-ID/domain-specific strings.
- src/openai_agent.py: validate_citation_format handles bracket/ID syntax, CURRENT
  context membership and inline/list equality. validate_cited_answer separately
  calls verify_grounding per claim and selected chunk. The claims/text/chunk_ids
  schema, prompt and final answer/citations contract are unchanged.
- Acceptance is based on exact canonical sequences, never a similarity score or
  unordered bag of words. Normalization handles NFC Unicode, whitespace, case,
  conservative punctuation spelling, reviewed contractions (cannot/can not etc.)
  and explicit same-unit aliases (hr/hours etc.). No conversion between units.
- Adjacent affirmative sentences may be joined with "and", preserving complete
  token order/subjects. This rewrite is disabled for negative, conditional, modal
  or quantified sentences. No unrestricted connective deletion or synonym list.
- Numeric signs/values, units, SI prefix case (mA vs MA), comparison operators,
  negation, conditions, modality and qualifiers such as maximum/minimum/about/
  recommended must not disappear. Exact excerpt acceptance preserves these
  protected facts from its containing sentence. A changed number/unit/condition
  cannot pass merely because most other words match. Question text is not treated
  as an evidence assertion.
- Unknown or unverifiable rewrites return FAIL/abstain. In particular, no generic
  rule equates "A, allowing B" with "A. B is possible": the former can introduce
  causality. This would be an unsafe relaxation just to make a recorded case pass.
- Events now record grounding_checks with claim/chunk, proof method or specific
  failure (numeric/unit/negation/condition/modality/qualifier/comparison mismatch,
  or unverified_paraphrase_or_added_information). Outer failure remains
  unsupported_cited_claim for backward-compatible consumers; cite-format errors
  remain invalid_or_missing_citations. No citation is guessed/appended/replaced.
- src/run_agent_dev.py adds grounding.py to future implementation-hash records;
  no inference configuration changed or executed.

## Tests

77/77 full unit tests PASS offline. New tests/test_grounding_rules.py has13 tests
covering verbatim, Unicode/punctuation, reviewed equivalent contractions/units,
ordered sentence composition, wrong values/units/signs/SI prefixes/operators,
negation reversal, new/omitted/changed conditions, modal strength, numeric token
boundaries, unsupported causal/invented facts, independent citation-format gates,
two claims/two supported sources and detailed rejection reasons.

Existing citation, structured-claims, retriever, provider and evidence-group tests
remain passing. A numeric-boundary positive fixture was adjusted from a fragment
that omitted "before operation" to a source containing only "6 hours"; preserving
an actual source condition is now a deliberate requirement. Its negative numeric
and sign cases still fail. No frozen benchmark or evaluator test labels changed.
All OpenAI interactions in unit tests are mocks; no live API or DEV/TEST run.
Frozen rebuild/hashes PASS. No Day06 access/write, commit or push in this task.

## Reliability limits and next step

This is a small proof-rule system, NOT a general semantic entailment verifier.
It cannot reliably interpret arbitrary paraphrases, pronouns, causal relations,
complex scope/condition exceptions across sentences, table geometry or omitted
question requirements. Unsupported language continues to abstain. Generic
canonicalization/excerpt guards do not prove global document consistency. Rules
are not a guarantee against every unsupported interpretation; human semantic
review remains necessary for benchmark answer/citation judgments.

No assertion is made that either prior q12 paraphrase now passes. The modal
sentence-joining restriction and causal "allowing" rewrite may still reject that
output, intentionally. No benchmark gold or question ID was used to add a special
acceptance path. This repair does not rewrite prior failed q12 results.

Recommended next work, requiring approval: inspect/extend synthetic adversarial
coverage for a specific justified equivalence before any paid run. For reliable
fully deterministic delivery, prefer extractive source spans selected explicitly
by the model (validated offsets/text) over a broad paraphrase matcher; a future
schema change for such spans would need separate review and is not implemented.
Alternatively, have a human review unverifiable paraphrases rather than silently
passing them. Do not spend another q12 call solely expecting unsupported rewrites
to pass. Stop here pending user decision.

Files: new src/grounding.py, tests/test_grounding_rules.py and this report;
modified src/openai_agent.py, src/run_agent_dev.py (hash list only), src/README.md,
tests/test_inline_citations.py (the synthetic fixture described above).
