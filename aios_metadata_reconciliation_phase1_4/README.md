# AIOS Metadata Reconciliation — Phase 1.4

## Purpose

Phase 1.4 performs the first narrowly scoped metadata reconciliation mutation.

It clears `Quick Win` only when a task is deferred to a future date.

## Mutation boundary

This package may update Notion only when both conditions are true:

- `Defer Until` is in the future
- `Quick Win` is checked

The mutation is only:

```text
Quick Win=false
```

It does not change:

- Execution Score
- Execution Rank
- Best Next Action
- Do = Today
- Focus / Focus Now
- evaluator scoring
- task names
- due dates
- defer dates

All non-Quick-Win findings remain diagnostics-only.

## Install

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_metadata_reconciliation_phase1_4.tar.gz
bash aios_metadata_reconciliation_phase1_4/install.sh
bash run.sh > test_run.log 2>&1
grep -E "METADATA RECONCILIATION|Metadata Reconciliation|Deferred future|Would clear Quick Win|Applying Quick Win|Clearing Quick Win|Quick Win cleared|Mutation error" test_run.log
```

## Expected successful output

```text
=== METADATA RECONCILIATION — PHASE 1.4: QUICK WIN DEFERRED CLEANUP ===
[Metadata Reconciliation] Deferred future tasks still surfaced: 1
[Metadata Reconciliation] Would clear Quick Win: 1
[Metadata Reconciliation] Applying Quick Win deferred cleanup: 1
[Metadata Reconciliation] Clearing Quick Win: Test pool water — Defer Until=2026-06-09
[Metadata Reconciliation] Quick Win cleared: 1
```

A second run should usually show:

```text
[Metadata Reconciliation] Quick Win deferred cleanup: 0
```

## Rollback

```bash
cd ~/LocalProjects/aios
bash tools/rollback_metadata_reconciliation_phase1.sh
```
