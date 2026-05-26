# Patch Notes — Phase 5 Policy-Driven Presentation Overlay Cleanup

## Changed

- Upgraded reconciliation version to `metadata-reconciliation-phase5-policy-driven-presentation-overlay-cleanup-v0.5.0`.
- Upgraded policy registry to `canonical-metadata-policy-v0.3.0`.
- Added policy-driven stale presentation overlay cleanup for `Quick Win`.

## Mutation boundary

This package may clear `Quick Win` only when a task is:

- closed/done
- future-deferred
- JDI

It does not mutate:

- `Do = Today`
- evaluator scores
- task titles/content
- deprecated `Focus Now` / `Strong Candidate`
- project metadata

## Expected clean-run log

```text
[Metadata Reconciliation] Policy stale presentation cleanup: 0
[Metadata Reconciliation] Policy stale execution cleanup: 0
Errors: 0
```
