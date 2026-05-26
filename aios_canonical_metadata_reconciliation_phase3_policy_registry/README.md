# AIOS Canonical Metadata Reconciliation — Phase 3 Policy Registry

This package introduces the first canonical metadata reconciliation foundation:

a declarative metadata policy registry at:

```text
core/metadata/policy.py
```

and updates:

```text
core/metadata/reconciliation.py
```

to use that registry for canonical field aliases and runtime policy status logging.

## Scope

This package does **not** change evaluator scoring, execution ranking, BNA selection, Quick Win selection, dashboard generation, task ingestion, or project cognition.

It adds a central policy layer for:

- canonical execution fields
- presentation overlays
- manual-only metadata
- deprecated execution fields
- lifecycle/eligibility signals

## Install

```bash
cd ~/LocalProjects/aios
bash aios_canonical_metadata_reconciliation_phase3_policy_registry/install.sh
bash aios_canonical_metadata_reconciliation_phase3_policy_registry/smoke_test.sh
```

## Rollback

```bash
cd ~/LocalProjects/aios
bash aios_canonical_metadata_reconciliation_phase3_policy_registry/rollback.sh
```
