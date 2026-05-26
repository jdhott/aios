# AIOS Canonical Metadata Reconciliation — Phase 5

Policy-driven presentation overlay cleanup.

This package extends canonical metadata reconciliation so Quick Win is cleaned by policy when it is stale:

- closed/done tasks
- future-deferred tasks
- JDI tasks

Quick Win remains presentation-only. This package does not change evaluator scoring, BNA ranking, dashboard selection, or `Do = Today`.

## Install

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_canonical_metadata_reconciliation_phase5_presentation_overlay_cleanup.tar.gz
bash aios_canonical_metadata_reconciliation_phase5_presentation_overlay_cleanup/install.sh
bash aios_canonical_metadata_reconciliation_phase5_presentation_overlay_cleanup/smoke_test.sh
```

## Rollback

```bash
cd ~/LocalProjects/aios
bash aios_canonical_metadata_reconciliation_phase5_presentation_overlay_cleanup/rollback.sh
```
