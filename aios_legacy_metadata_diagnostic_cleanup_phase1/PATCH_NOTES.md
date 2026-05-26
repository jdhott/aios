# AIOS Legacy Metadata Diagnostic Cleanup — Phase 1

## Purpose

This package performs the first cleanup step after the legacy metadata audit.

It updates:

```text
core/metadata/reconciliation.py
```

## What changed

- Bumps reconciliation version to `metadata-reconciliation-phase2-legacy-diagnostic-cleanup-v0.2.4`.
- Removes stale reconciliation diagnostics that treated `Do = Today` as an execution surfacing mismatch.
- Stops treating `Focus`, `Focus Now`, and `Strong Candidate` as reconciliation surfaces.
- Keeps canonical execution diagnostics focused on:
  - `Best Next Action`
  - `Execution Score`
  - `Execution Rank`
- Keeps `Quick Win` as passive presentation metadata.
- Preserves existing safe mutations:
  - clear `Quick Win` only when future-deferred
  - clear meaningful closed/done `Execution Score` / `Execution Rank`
  - canonical `Execution Rank` rewrite for active ranked rows

## What did not change

- No evaluator logic changed.
- No execution scoring changed.
- No dashboard generation changed.
- No ingestion logic changed.
- No task title/content mutation changed.
- `Do = Today` remains manual-only metadata.

## Install

From your project root:

```bash
cd ~/LocalProjects/aios
bash /path/to/aios_legacy_metadata_diagnostic_cleanup_phase1/install.sh
bash /path/to/aios_legacy_metadata_diagnostic_cleanup_phase1/smoke_test.sh
```

## Rollback

From your project root:

```bash
cd ~/LocalProjects/aios
bash /path/to/aios_legacy_metadata_diagnostic_cleanup_phase1/rollback.sh
```
