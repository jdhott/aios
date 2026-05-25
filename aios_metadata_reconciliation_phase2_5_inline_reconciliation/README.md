# AIOS Metadata Reconciliation — Phase 2.5

Inline Reconciliation + No-Op Rank Rewrite.

This package:
- removes the late `atexit` reconciliation pass,
- runs reconciliation inline before run summary / notification / dashboard,
- skips Execution Rank clear/rewrite when `changed=0`.

Install:

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_metadata_reconciliation_phase2_5_inline_reconciliation.tar.gz
bash aios_metadata_reconciliation_phase2_5_inline_reconciliation/install.sh
bash aios_metadata_reconciliation_phase2_5_inline_reconciliation/smoke_test.sh
```

Test:

```bash
bash run.sh > test_run.log 2>&1
grep -E "Runtime Lock|METADATA RECONCILIATION|Metadata Reconciliation|Execution Rank Diagnostics|Applying true execution rank rewrite|Execution rank rewrite skipped|Execution ranks rewritten canonically|atexit hook disabled|Mutation error" test_run.log
```
