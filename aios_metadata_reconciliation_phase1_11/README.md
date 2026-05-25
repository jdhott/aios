# AIOS Metadata Reconciliation Phase 1.11

Install from the AIOS project root:

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_metadata_reconciliation_phase1_11.tar.gz
bash aios_metadata_reconciliation_phase1_11/install.sh
bash run.sh > test_run.log 2>&1
grep -E "METADATA RECONCILIATION|Metadata Reconciliation|Open tasks with Do = Today|Open Best Next Action|Open Best Next Action tasks without|JDI tasks with forbidden|Closed/done|Quick Win deferred cleanup|Closed/done execution cleanup|Mutation error" test_run.log
```

This package keeps previous validated cleanups and adds explicit zero-count diagnostics for open-surface mismatch checks.
