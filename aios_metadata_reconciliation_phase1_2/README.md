# AIOS Metadata Reconciliation — Phase 1.2

Diagnostics-only update for the canonical metadata reconciliation workstream.

This package fixes the Phase 1.1 visibility problem: per-task finding details are now emitted with the `[Metadata Reconciliation]` prefix, so they appear in the same grep command as the summary lines.

Safe behavior remains unchanged:

- no Notion mutations
- no evaluator/scoring changes
- no execution ranking changes
- no dashboard behavior changes

Expected detail output now looks like:

```text
[Metadata Reconciliation] Deferred future tasks still surfaced: 1
[Metadata Reconciliation] Finding detail: Deferred future tasks still surfaced — Example Task — Defer Until=2026-06-01, Best Next Action=true, Do = Today=true, Execution Rank=3
```

## Install

From the project root:

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_metadata_reconciliation_phase1_2.tar.gz
bash aios_metadata_reconciliation_phase1_2/install.sh
bash run.sh > test_run.log 2>&1
grep -E "METADATA RECONCILIATION|Metadata Reconciliation|Finding detail|Deferred future" test_run.log
```

## Rollback

The installer creates a timestamped backup and writes the latest backup path to:

```text
.metadata_reconciliation_phase1_2_last_backup
```

You can also run:

```bash
bash tools/rollback_metadata_reconciliation_phase1.sh
```
