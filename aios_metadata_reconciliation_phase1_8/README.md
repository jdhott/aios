# AIOS Metadata Reconciliation Phase 1.8

First closed/done task execution cleanup mutation package.

Retains the validated Phase 1.4 mutation boundary: clears `Quick Win` only when `Defer Until` is in the future.

New in Phase 1.8: clears meaningful stale `Execution Score` and `Execution Rank` on closed/done tasks only. Default `Execution Score=0` remains ignored as noise.

No evaluator, ranking, Best Next Action, Do = Today, Focus, or task-content logic is changed.

## Install

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_metadata_reconciliation_phase1_8.tar.gz
bash aios_metadata_reconciliation_phase1_8/install.sh
bash run.sh > test_run.log 2>&1
grep -E "METADATA RECONCILIATION|Metadata Reconciliation|Closed/done|Applying closed|Clearing closed|metadata cleared|Quick Win cleared|Mutation error" test_run.log
```
