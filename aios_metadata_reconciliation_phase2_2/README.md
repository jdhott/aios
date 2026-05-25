# AIOS Metadata Reconciliation Phase 2.2

Deterministic rank diagnostics package.

This package preserves the validated Phase 2.0/2.1 reconciliation behavior and adds grep-visible diagnostics for the execution rank pipeline:

- active ranked rows observed
- skipped/excluded counts
- missing persisted ranks
- duplicate persisted ranks
- current persisted-rank order preview
- deterministic score/title/page-id order preview
- order mismatch examples

The goal is to diagnose intermittent missing ranks such as skipped rank 3 before changing ranking logic.

## Install

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_metadata_reconciliation_phase2_2.tar.gz
bash aios_metadata_reconciliation_phase2_2/install.sh
bash run.sh > test_run.log 2>&1
grep -E "METADATA RECONCILIATION|Metadata Reconciliation|Metadata Persistence Guard|Execution Rank Diagnostics|Canonicalizing Execution Rank|Execution rank canonicalization|Mutation error" test_run.log
```
