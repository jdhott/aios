# AIOS Metadata Reconciliation Phase 1.5

Adds diagnostics-only detection for closed/done tasks that still carry active execution or presentation metadata.

Retains the validated Phase 1.4 mutation boundary: only clears `Quick Win` when `Defer Until` is in the future.

## Install

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_metadata_reconciliation_phase1_5.tar.gz
bash aios_metadata_reconciliation_phase1_5/install.sh
bash run.sh > test_run.log 2>&1
grep -E "METADATA RECONCILIATION|Metadata Reconciliation|Closed/done|Done tasks|Deferred future|Would clear Quick Win|Applying Quick Win|Clearing Quick Win|Quick Win cleared|Mutation error" test_run.log
```
