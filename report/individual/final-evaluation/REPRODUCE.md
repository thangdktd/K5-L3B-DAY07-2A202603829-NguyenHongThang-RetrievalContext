# Reproduce and inspect Day07

Start at repository root in PowerShell. Python3.13.7 was used.

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r src/requirements.txt
.venv/Scripts/python.exe -X utf8 src/build_final_benchmark.py --check
.venv/Scripts/python.exe -X utf8 -m unittest discover -s tests -v
```

Do not regenerate frozen files. The official builder checks freeze; legacy scripts cannot overwrite a frozen benchmark. Read data/README.md for corpus conversion and deterministic rebuild verification.

Place OPENAI_API_KEY only in local ignored .env or environment. No key is included. Keep Day06 local database/model available read-only; defaults and connection checks are in src/retrievers.py. Day06 path is D:/VinUniAI/K5-L3B-Day06-2A202603829-DataIngestionEngineering, model models/all-MiniLM-L6-v2, local DB day6_lab; connection environment is read from Day06 starter/.env without printing secrets. Exact corpus/model/run fingerprints are in runtime.json/report. To reproduce elsewhere, provide equivalent permitted assets and compatible connection settings rather than replacing embeddings.

Already executed protocol (API calls incurred):

```powershell
.venv/Scripts/python.exe -X utf8 src/run_agent_suite.py --split dev
.venv/Scripts/python.exe -X utf8 src/evaluate_agent_suite.py --split dev --prepare-reviews
# Directly inspect each unchanged final output/context; complete reviews.json.
.venv/Scripts/python.exe -X utf8 src/evaluate_agent_suite.py --split dev
.venv/Scripts/python.exe -X utf8 src/evaluate_agent_suite.py --lock
.venv/Scripts/python.exe -X utf8 src/run_agent_suite.py --split test --resume
.venv/Scripts/python.exe -X utf8 src/evaluate_agent_suite.py --split test --prepare-reviews
# Directly inspect all5 answerable and2 unanswerable TEST outputs per profile.
.venv/Scripts/python.exe -X utf8 src/evaluate_agent_suite.py --split test
```

Do not replay TEST to improve scores. Existing completed cases are protected; --resume skips completed cases, and interrupted started cases are recorded rather than silently replayed. A separate future replication is a new experiment and must not replace these held-out results. Never tune using this TEST. Offline evaluator can inspect existing artifacts without any API calls; do not edit locked DEV reviews/config.

Exact inference source snapshot and SHA hashes are in source_snapshot and final_config_lock.json. Hashes identify exact bytes including line endings. New artifacts use .gitattributes; for a checkout that converts existing tracked source line endings, use the source_snapshot bytes for replay and verify hashes before running. Do not silently rewrite the original lock. Unit tests are mocks/offline, not substitutes for real evaluation.

Submission: report/individual/2A202603829_NguyenHongThang.md; source/tests/dependency pins, frozen data and permitted artifacts listed in submission_inventory.json. Historical traces remain under report/individual/checkpoint3b-* for error history and are excluded from final metrics. scratch and local virtualenv are not submission requirements. Review permission before publishing chunks/full-text traces; grader access is not configured automatically.

Suggested Git commands AFTER user approval and source-rights review (not executed):

```powershell
git status --short
git add .gitattributes .env.example src tests data report/individual
# Review staging for secrets, source redistribution rights and irrelevant scratch files.
git diff --cached --stat
git diff --cached --check
git commit -m "Complete Day07 retrieval and agent evaluation"
git push -u origin main
```

Never stage .env; gitignore protects it. Confirm origin is the personal repo, not class upstream, and grant grader access manually. Do not publish protected source data until permission is confirmed.
