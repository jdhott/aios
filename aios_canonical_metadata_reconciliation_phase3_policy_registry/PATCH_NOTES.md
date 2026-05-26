# Patch Notes — Canonical Metadata Reconciliation Phase 3 Policy Registry

## Version

- Reconciliation: `metadata-reconciliation-phase3-canonical-policy-registry-v0.3.0`
- Policy registry: `canonical-metadata-policy-v0.1.0`

## Changed

- Added `core/metadata/policy.py` as the first declarative canonical metadata policy registry.
- Updated reconciliation to source canonical aliases from the policy registry.
- Added grep-visible runtime policy lines:
  - canonical execution fields
  - presentation overlays
  - manual-only fields
  - deprecated execution fields ignored by reconciliation
- Preserved existing safe mutation boundaries:
  - clear stale Quick Win only when future-deferred
  - clear stale Execution Score / Execution Rank on closed/done tasks
  - canonicalize active Execution Rank sequence

## Not Changed

- No evaluator tuning.
- No ranking behavior changes.
- No Quick Win selection changes.
- No dashboard changes.
- No automatic `Do = Today` behavior.
- No Focus / Focus Now / Strong Candidate mutation.
