# AIOS Metadata Reconciliation — Phase 2.4

Runtime Lock + Candidate Set Alignment Diagnostics.

This package adds a runtime lock wrapper to prevent overlapping AIOS runs and installs a candidate-set alignment probe note. It is intentionally conservative because the logs showed two issues:

- diagnostics saw 11 active ranked rows
- rewrite saw 24 active rows
- the process may be running twice / overlapping

Install:

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_metadata_reconciliation_phase2_4_lock_alignment.tar.gz
bash aios_metadata_reconciliation_phase2_4_lock_alignment/install.sh
```

Test:

```bash
bash run.sh > test_run.log 2>&1
grep -E "Runtime Lock|Candidate Set Alignment|Execution Rank Diagnostics|Applying true execution rank rewrite|Skipping execution rank rewrite|Execution ranks rewritten canonically|Mutation error" test_run.log
```
