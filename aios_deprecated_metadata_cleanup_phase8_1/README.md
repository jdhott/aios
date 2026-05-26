# AIOS Deprecated Metadata Cleanup — Phase 8.1

This package promotes the validated Phase 8 governance anomaly signal for deprecated execution-era metadata into a narrow reconciliation cleanup.

It clears checked legacy boolean fields only:

- `Strong Candidate`
- `Focus Now` / `Focus`

It does **not** change:

- evaluator scoring
- execution ranking
- Best Next Action selection
- Quick Win behavior
- Do = Today manual pin behavior
- task titles or content

## Install

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_deprecated_metadata_cleanup_phase8_1.tar.gz
bash aios_deprecated_metadata_cleanup_phase8_1/install.sh ~/LocalProjects/aios
bash aios_deprecated_metadata_cleanup_phase8_1/smoke_test.sh ~/LocalProjects/aios
python3 run_aios.py 2>&1 | tee test_run.log
grep -E 'PHASE 8.1|deprecated metadata|Anomaly health|deprecated_metadata_seen|Errors:' test_run.log
```

## Rollback

```bash
cd ~/LocalProjects/aios
bash aios_deprecated_metadata_cleanup_phase8_1/rollback.sh ~/LocalProjects/aios
```
