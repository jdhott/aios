# AIOS Canonical Metadata Reconciliation — Phase 6

Governance telemetry summary.

This package adds a compact reconciliation summary to the logs so normal run review can confirm metadata governance health without scanning every detailed diagnostic row.

It does not change evaluator scoring, BNA ranking, dashboard selection, Quick Win selection, or `Do = Today`.

## Install

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_canonical_metadata_reconciliation_phase6_governance_telemetry_summary.tar.gz
bash aios_canonical_metadata_reconciliation_phase6_governance_telemetry_summary/install.sh
bash aios_canonical_metadata_reconciliation_phase6_governance_telemetry_summary/smoke_test.sh
```

## Rollback

```bash
cd ~/LocalProjects/aios
bash aios_canonical_metadata_reconciliation_phase6_governance_telemetry_summary/rollback.sh
```
