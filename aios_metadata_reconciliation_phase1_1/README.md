# AIOS Metadata Reconciliation — Phase 1.1

Diagnostics-only update for the canonical metadata reconciliation workstream.

This package keeps Phase 1 safe behavior intact:

- no Notion mutations
- no evaluator/scoring changes
- no execution ranking changes
- no dashboard behavior changes

It upgrades the reconciliation diagnostic output so each finding includes the active metadata fields that caused the issue, for example:

```text
Deferred future tasks still surfaced: 1
  - Example Task — Defer Until=2026-06-01, Best Next Action=true, Do = Today=true, Execution Rank=3
```

## Install

From the project root:

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_metadata_reconciliation_phase1_1.tar.gz
bash aios_metadata_reconciliation_phase1_1/install.sh
bash run.sh > test_run.log 2>&1
grep -E "METADATA RECONCILIATION|Metadata Reconciliation|Deferred future" test_run.log
```

## Rollback

The installer creates a timestamped backup and writes the latest backup path to:

```text
.metadata_reconciliation_phase1_last_backup
```

You can also run:

```bash
bash tools/rollback_metadata_reconciliation_phase1.sh
```
