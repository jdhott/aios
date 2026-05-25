# AIOS Metadata Reconciliation Phase 2.0

Adds an early closed-task execution persistence guard.

This package preserves the validated Phase 1 cleanups and diagnostics, then adds a guard that prevents closed/done tasks from receiving new non-null `Execution Score` or `Execution Rank` writes.

The guard is narrow:

- It only intercepts Notion page PATCH calls.
- It only acts when the target page is known to be closed/done in runtime task objects.
- It only strips non-null `Execution Score` / `Execution Rank` writes.
- It allows cleanup writes that set those fields to `null`.

## Install

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_metadata_reconciliation_phase2_0.tar.gz
bash aios_metadata_reconciliation_phase2_0/install.sh
bash run.sh > test_run.log 2>&1
grep -E "METADATA RECONCILIATION|Metadata Reconciliation|Metadata Persistence Guard|Closed/done|Quick Win deferred cleanup|Closed/done execution cleanup|Mutation error" test_run.log
```
