# Patch Notes — Governance Anomaly Diagnostics Phase 8

## What changed

- Bumps reconciliation version to `metadata-reconciliation-phase8-governance-anomaly-diagnostics-v0.8.0`.
- Adds read-only anomaly counters:
  - `ranked_without_score`
  - `score_without_rank`
  - `bna_without_rank_or_score`
  - `quickwin_bna_overlap`
  - `orphaned_today_flags`
  - `deprecated_metadata_seen`
  - `future_deferred_surface`
  - `closed_or_done_surface`
  - `duplicate_execution_ranks`
- Adds a compact `=== GOVERNANCE ANOMALY DIAGNOSTICS ===` log block.
- Adds anomaly totals into the existing metadata governance telemetry summary.

## Mutation boundary

No new mutation paths are introduced.

This phase is diagnostics-only and does not alter:

- Execution Score
- Execution Rank
- Best Next Action
- Quick Win
- Do = Today
- Focus Now
- Strong Candidate
- evaluator scoring
- ranking persistence

## Why this is the right first step

The current architecture is stable enough that the next risk is silent metadata drift or authority leakage, not scoring behavior. This patch makes those problems visible before any repair/backfill tooling is added.
