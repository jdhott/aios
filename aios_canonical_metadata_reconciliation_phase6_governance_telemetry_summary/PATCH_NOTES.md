# Patch Notes — Phase 6 Governance Telemetry Summary

## Changed

- Upgraded reconciliation version to `metadata-reconciliation-phase6-governance-telemetry-summary-v0.6.0`.
- Upgraded policy registry to `canonical-metadata-policy-v0.4.0`.
- Added a compact `METADATA GOVERNANCE TELEMETRY SUMMARY` block to each reconciliation run.
- Summarizes observed task counts, reconciliation findings, stale cleanup candidates, active ranked rows, rank rewrite changes, and authority boundaries.

## Mutation boundary

This package does not expand mutation scope.

Existing policy-driven cleanup remains unchanged:

- stale canonical execution cleanup
- stale Quick Win presentation cleanup
- canonical execution rank rewrite when needed

It does not mutate:

- `Do = Today`
- evaluator scores beyond existing execution reconciliation rules
- task titles/content
- deprecated `Focus Now` / `Strong Candidate`
- project metadata

## Expected clean-run log

```text
=== METADATA GOVERNANCE TELEMETRY SUMMARY ===
[Metadata Governance] Reconciliation signals: findings=0; stale_presentation_candidates=0; stale_execution_candidates=0; ...
[Metadata Governance] Status: clean
Errors: 0
```
