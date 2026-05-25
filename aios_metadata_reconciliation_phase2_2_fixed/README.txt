AIOS Metadata Reconciliation — Phase 2.2 Fixed

This package corrects the smoke test assertion bug from the prior upload.
The smoke test now validates PHASE 2.2 correctly instead of PHASE 2.1.

Suggested test:
bash run.sh > test_run.log 2>&1
grep -E "Execution Rank Diagnostics|Execution rank canonicalization|Canonicalizing Execution Rank|Rank gap diagnostic|Metadata Persistence Guard" test_run.log
