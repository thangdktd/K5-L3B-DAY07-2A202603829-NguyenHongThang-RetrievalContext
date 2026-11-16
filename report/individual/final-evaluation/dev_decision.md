# DEV decision — written before TEST

Select Hybrid RRF/2400 as the final Agent retrieval/context configuration.
The controller, structured claims schema, system prompt, grounding rules and
common API parameters remain unchanged after this decision.

Fair same-code DEV comparison, all17 cases per profile:
- Selected: original-query Hit@1 11/15; Evidence Hit@3 15/15; final context15/15;
  grounded answer mean1.20/2; final valid citations10/10; abstention2/2;
  false abstention6/15;37 API attempts; token estimate$0.0185664.
- Baseline TF-IDF800: original-query Hit@1 10/15; Hit@3 13/15; final context9/15;
  grounded mean0.80/2; valid citations6/7; abstention1/2; false abstention9/15;
  46 API attempts; token estimate$0.0178192.

Primary criteria declared before DEV: complete retrieval/context evidence,
grounded answer quality, citation support and false abstention, with token cost
and latency as tie-breakers. The selected profile wins quality and scope safety
at a small measured cost increase. It uses fewer API attempts in this DEV run
because baseline frequently needs more searches. No statistical inference from
one run is claimed. Six selected answerable cases still fail due to the existing
validator and are scored0; do not weaken validation or rewrite those outputs.

Common settings: gpt-4.1-mini (observed snapshot2025-04-14), temperature0,
max3 searches, top3, output600 tokens/request, timeout60s; SDK retries0 and wrapper
one retry only for transient failures, audited. RRF candidate20/branch, k60;
no metadata filter. Final source hashes/snapshots are in suite_manifest.json and
source_snapshot/. The final_config_lock.json is generated next with reviewed
DEV artifact hashes, before any TEST request. TEST will compare both profiles
on the same7 held-out cases once. No changes based on TEST are permitted.
