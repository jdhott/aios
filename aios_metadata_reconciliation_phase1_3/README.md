# AIOS Metadata Reconciliation — Phase 1.3

Diagnostics-only Quick Win reconciliation preview.

This package keeps reconciliation read-only, but adds an explicit preview for stale Quick Win flags on tasks deferred to a future date.

Safe behavior:

- no Notion mutations
- no evaluator/scoring changes
- no execution ranking changes
- no dashboard behavior changes

Expected output includes:

```text
[Metadata Reconciliation] Deferred future tasks still surfaced: 1
[Metadata Reconciliation] Finding detail: Deferred future tasks still surfaced — Test pool water — Defer Until=2026-06-09, Quick Win=true, Execution Score=0
[Metadata Reconciliation] Would clear Quick Win: 1
[Metadata Reconciliation] Finding detail: Would clear Quick Win — Test pool water — Reason: deferred until future date; Defer Until=2026-06-09, Quick Win=true, Execution Score=0
[Metadata Reconciliation] Preview only. No Notion mutations performed.
```

## Install

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_metadata_reconciliation_phase1_3.tar.gz
bash aios_metadata_reconciliation_phase1_3/install.sh
bash run.sh > test_run.log 2>&1
grep -E "METADATA RECONCILIATION|Metadata Reconciliation|Finding detail|Deferred future|Would clear Quick Win" test_run.log
```

## Rollback

```bash
bash tools/rollback_metadata_reconciliation_phase1.sh
```
