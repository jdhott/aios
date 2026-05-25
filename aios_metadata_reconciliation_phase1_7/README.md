# AIOS Metadata Reconciliation Phase 1.7

Noise-reduction package for closed/done task diagnostics.

Retains the validated Phase 1.4 mutation boundary: only clears `Quick Win` when `Defer Until` is in the future.

Changes closed/done diagnostics so `Execution Score=0` by itself is treated as default/noise and is not counted as a reconciliation finding. Meaningful stale metadata still includes `Execution Rank`, `Best Next Action`, `Do = Today`, `Quick Win`, `Focus Now`, or `Execution Score > 0`.

## Install

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_metadata_reconciliation_phase1_7.tar.gz
bash aios_metadata_reconciliation_phase1_7/install.sh
bash run.sh > test_run.log 2>&1
grep -E "METADATA RECONCILIATION|Metadata Reconciliation|Closed/done|Would clear closed|Fields present|Execution Score=0|Quick Win cleared|Mutation error" test_run.log
```
