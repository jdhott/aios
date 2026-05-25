# AIOS Metadata Reconciliation Phase 1.12

Diagnostics-first reconciliation package.

This release keeps the validated mutations from earlier phases:

- Clear stale `Quick Win` on future-deferred tasks.
- Clear meaningful `Execution Score` / `Execution Rank` from closed/done tasks.

It adds diagnostics-only visibility for future-deferred tasks carrying execution or presentation metadata:

- `Execution Rank`
- meaningful `Execution Score`
- `Best Next Action`
- `Do = Today`

No new mutation is added for these deferred execution/presentation diagnostics.

## Install

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_metadata_reconciliation_phase1_12.tar.gz
bash aios_metadata_reconciliation_phase1_12/install.sh
bash run.sh > test_run.log 2>&1
grep -E "METADATA RECONCILIATION|Metadata Reconciliation|Deferred future tasks with|JDI tasks with forbidden|Open tasks with Do = Today|Open Best Next Action|Closed/done|Quick Win deferred cleanup|Closed/done execution cleanup|Mutation error" test_run.log
```
