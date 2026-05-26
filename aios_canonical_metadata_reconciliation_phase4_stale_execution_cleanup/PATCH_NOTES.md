# Patch Notes — Canonical Metadata Reconciliation Phase 4

## Version

- Reconciliation: `metadata-reconciliation-phase4-policy-driven-stale-execution-cleanup-v0.4.0`
- Policy: `canonical-metadata-policy-v0.2.0`

## Summary

Adds the first policy-driven stale execution cleanup action. Reconciliation now clears stale canonical execution state from closed/done, future-deferred, and JDI tasks.

## Mutated fields

Only these canonical execution fields may be cleared by this patch:

- `Execution Score`
- `Execution Rank`
- `Best Next Action`

## Preserved fields

These are intentionally not mutated:

- `Do = Today` — manual-only user pin
- `Quick Win` — governed separately; only existing deferred Quick Win cleanup remains active
- `Focus Now` — deprecated and ignored
- `Strong Candidate` — deprecated and ignored

## Safety notes

- Existing rank canonicalization remains unchanged.
- Existing Quick Win deferred cleanup remains unchanged.
- No evaluator, dashboard, ingestion, or project-cognition code is changed.
