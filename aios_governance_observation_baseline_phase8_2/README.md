# AIOS Governance Observation Baseline — Phase 8.2

This package adds a final, cron-friendly observation baseline block after governance diagnostics and cleanup planning.

It is designed for the current post-8.1 state where governance is clean and the next step is normal runtime observation.

It does **not** change:

- evaluator scoring
- execution ranking
- Best Next Action selection
- Quick Win behavior
- Do = Today manual pin behavior
- task titles or content
- mutation scope

## What it adds

A final block like:

```text
=== GOVERNANCE OBSERVATION BASELINE ===
[Metadata Governance] Observation baseline: status=clean; anomalies=0; planned_mutations=0; cleanup_errors=0; observe_next_cron=no
[Metadata Governance] Observation detail: stale_presentation=0; stale_execution=0; deprecated_cleanup=0; rank_rewrite_changes=0
[Metadata Governance] Observation layer is read-only and does not alter execution authority.
```

If a cleanup or anomaly appears, the status becomes `stabilizing` or `attention_required`.

## Install

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_governance_observation_baseline_phase8_2.tar.gz
bash aios_governance_observation_baseline_phase8_2/install.sh ~/LocalProjects/aios
bash aios_governance_observation_baseline_phase8_2/smoke_test.sh ~/LocalProjects/aios
python3 run_aios.py 2>&1 | tee test_run.log
grep -E 'PHASE 8.2|Observation baseline|Anomaly health|deprecated_metadata_seen|Errors:' test_run.log
```

## Rollback

```bash
cd ~/LocalProjects/aios
bash aios_governance_observation_baseline_phase8_2/rollback.sh ~/LocalProjects/aios
```
