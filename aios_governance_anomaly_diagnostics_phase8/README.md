# AIOS Governance Anomaly Diagnostics — Phase 8

This package adds compact, read-only governance anomaly diagnostics to `core.metadata.reconciliation`.

It does **not** change ranking, evaluator scoring, dashboard selection, Quick Win assignment, Best Next Action selection, or mutation policy.

## Install

```bash
cd ~/LocalProjects/aios
bash /path/to/aios_governance_anomaly_diagnostics_phase8/install.sh ~/LocalProjects/aios
bash /path/to/aios_governance_anomaly_diagnostics_phase8/smoke_test.sh ~/LocalProjects/aios
python3 run_aios.py 2>&1 | tee test_run.log
grep -E 'GOVERNANCE ANOMALY|Anomaly health|Metadata Governance|Errors:' test_run.log
```

## Rollback

```bash
cd ~/LocalProjects/aios
bash /path/to/aios_governance_anomaly_diagnostics_phase8/rollback.sh ~/LocalProjects/aios
```
