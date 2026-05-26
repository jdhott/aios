# Patch Notes — Phase 8.2 Governance Observation Baseline

## Goal

Support the next recommended step: observe stable governance runtime under normal cron/use without adding new automation or changing execution behavior.

## Changes

- Bumps reconciliation version to `metadata-reconciliation-phase8-2-governance-observation-baseline-v0.8.2`.
- Adds `format_governance_observation_baseline()`.
- Emits a final compact observation block after reconciliation cleanup sections.
- Reports:
  - `status=clean | stabilizing | attention_required`
  - anomaly count
  - planned mutation count
  - cleanup error count
  - stale presentation cleanup count
  - stale execution cleanup count
  - deprecated metadata cleanup count
  - rank rewrite change count

## Mutation Boundary

No new mutations are introduced.

Existing Phase 8.1 behavior remains unchanged:

- stale policy cleanup remains as previously governed
- deprecated `Strong Candidate` / `Focus Now` cleanup remains as previously validated
- execution rank canonicalization remains unchanged

Not changed:

- `Execution Score`
- `Execution Rank`
- `Best Next Action`
- `Quick Win`
- `Do = Today`
- evaluator logic
- dashboard logic
- task titles/content
