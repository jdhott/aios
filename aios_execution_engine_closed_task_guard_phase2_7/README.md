# AIOS Execution Engine Closed-Task Guard — Phase 2.7

Fixes the missing-rank issue caused by Execution Engine ranking a closed/done task.

Install:

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_execution_engine_closed_task_guard_phase2_7.tar.gz
bash aios_execution_engine_closed_task_guard_phase2_7/install.sh
bash aios_execution_engine_closed_task_guard_phase2_7/smoke_test.sh
```

Test:

```bash
bash run.sh > test_run.log 2>&1
grep -E "Execution Engine V2|Closed/done tasks excluded|Canonical persistence row|Write payload|Execution Rank Diagnostics|Execution rank rewrite skipped|update failed|Mutation error" test_run.log
```
