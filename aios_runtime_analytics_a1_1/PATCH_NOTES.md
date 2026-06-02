# AIOS Runtime Analytics A1.1 — Hardened Analytics Ledger

## Purpose

Hardens A1.0 by making the analytics ledger more useful for evaluator review and weekly monitoring.

## Changes

- Replaces `core/runtime_analytics.py` with A1.1.
- Moves the runtime analytics hook so the summary prints after the BNA/provenance block when D1.3 is present.
- Adds BNA metadata provenance to `logs/runtime_analytics_latest.json`.
- Adds provenance mix columns to `logs/runtime_analytics.csv`:
  - `bna_explicit_marker_count`
  - `bna_ai_inferred_count`
  - `bna_manual_or_unknown_count`
  - `bna_provenance_mix_json`
  - `bna_provenance_json`
- Preserves existing analytics CSV rows by migrating the CSV header when needed.
- Backs up the pre-A1.1 CSV automatically before schema migration.

## Governance

- Read-only analytics only.
- No Notion task mutations.
- No evaluator weight changes.
- No ranking changes.
- No execution-authority changes.
- AI Processing Log lookup is read-only and nonfatal.

## Outputs

- `logs/runtime_analytics.csv`
- `logs/runtime_analytics_latest.json`
- `=== AIOS RUNTIME ANALYTICS SUMMARY A1.1 ===`

## Rollback

Use:

```bash
bash aios_runtime_analytics_a1_1/rollback.sh
```
