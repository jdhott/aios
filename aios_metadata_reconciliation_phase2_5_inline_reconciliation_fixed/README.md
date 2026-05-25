# AIOS Metadata Reconciliation — Phase 2.5 Fixed

Fixes the previous installer failure.

Changes:
- Removes the late `atexit` reconciliation hook.
- Runs reconciliation inline before `print_run_summary()` / `notify_run_summary()`.
- Skips Execution Rank clear/rewrite when `changed=0`.

Install:

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_metadata_reconciliation_phase2_5_inline_reconciliation_fixed.tar.gz
bash aios_metadata_reconciliation_phase2_5_inline_reconciliation_fixed/install.sh
bash aios_metadata_reconciliation_phase2_5_inline_reconciliation_fixed/smoke_test.sh
```

Test:

```bash
bash run.sh > test_run.log 2>&1
grep -E "Runtime Lock|METADATA RECONCILIATION|Metadata Reconciliation|Execution Rank Diagnostics|Applying true execution rank rewrite|Execution rank rewrite skipped|Execution ranks rewritten canonically|atexit hook disabled|Mutation error" test_run.log
```
