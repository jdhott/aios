# AIOS Canonical Metadata Reconciliation — Phase 4

## Policy-Driven Stale Execution Cleanup

This package advances canonical metadata reconciliation from a declarative policy registry into the first policy-driven cleanup action.

## Scope

Updated files:

- `core/metadata/policy.py`
- `core/metadata/reconciliation.py`

## What changes

Phase 4 clears stale canonical execution fields from tasks that must not carry execution state:

- closed / done tasks
- future-deferred tasks
- JDI tasks

The canonical execution fields are now read from the policy registry:

- `Execution Score`
- `Execution Rank`
- `Best Next Action`

## What does not change

This package does **not** change:

- evaluator scoring
- execution ranking logic
- dashboard generation
- Quick Win selection
- task titles or content
- manual `Do = Today` pins
- deprecated `Focus Now` / `Strong Candidate` fields

## Install

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_canonical_metadata_reconciliation_phase4_stale_execution_cleanup.tar.gz
bash aios_canonical_metadata_reconciliation_phase4_stale_execution_cleanup/install.sh
bash aios_canonical_metadata_reconciliation_phase4_stale_execution_cleanup/smoke_test.sh
```

## Rollback

```bash
cd ~/LocalProjects/aios
bash aios_canonical_metadata_reconciliation_phase4_stale_execution_cleanup/rollback.sh
```
