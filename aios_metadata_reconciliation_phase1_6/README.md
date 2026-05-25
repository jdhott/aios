# AIOS Metadata Reconciliation Phase 1.6

Adds preview-only logging for exactly which closed/done task execution or presentation metadata fields would be cleared in a future package.

Retains the validated Phase 1.4 mutation boundary: only clears `Quick Win` when `Defer Until` is in the future.

## Install

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_metadata_reconciliation_phase1_6.tar.gz
bash aios_metadata_reconciliation_phase1_6/install.sh
bash run.sh > test_run.log 2>&1
grep -E "METADATA RECONCILIATION|Metadata Reconciliation|Closed/done|Would clear closed|Fields present|Quick Win cleared|Mutation error" test_run.log
```
