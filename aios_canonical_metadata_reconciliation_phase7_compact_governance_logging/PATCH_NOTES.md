# Patch Notes

Version: `metadata-reconciliation-phase7-compact-governance-logging-v0.7.0`

## Summary

Phase 7 makes normal AIOS logs easier to review by keeping the compact metadata governance summary and moving older high-volume diagnostics behind explicit environment flags.

## Files changed

- `core/metadata/reconciliation.py`
- `core/metadata/policy.py`
- `execution_engine_v2.py`

## Rollback

```bash
cd ~/LocalProjects/aios
bash aios_canonical_metadata_reconciliation_phase7_compact_governance_logging/rollback.sh
```
