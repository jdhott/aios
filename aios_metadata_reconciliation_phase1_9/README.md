# AIOS Metadata Reconciliation Phase 1.9

Open surface mismatch diagnostics package.

Retains validated mutations from earlier phases:

- Clear `Quick Win` only when `Defer Until` is in the future.
- Clear meaningful `Execution Score` / `Execution Rank` only on closed/done tasks.

New in Phase 1.9: diagnostics-only checks for open-task execution surface mismatches:

- `Do = Today` without `Best Next Action`
- `Best Next Action` not surfaced in `Do = Today`
- `Best Next Action` without `Execution Rank`
- `Best Next Action` without meaningful `Execution Score`

No mutations are applied for the new open-task diagnostics.

## Install

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_metadata_reconciliation_phase1_9.tar.gz
bash aios_metadata_reconciliation_phase1_9/install.sh
bash run.sh > test_run.log 2>&1
grep -E "METADATA RECONCILIATION|Metadata Reconciliation|Open tasks with Do = Today|Open Best Next Action|Closed/done|Quick Win deferred cleanup|Closed/done execution cleanup|Mutation error" test_run.log
```
