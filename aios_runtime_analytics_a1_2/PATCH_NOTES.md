# AIOS Runtime Analytics A1.2

Final analytics hardening pass.

## What changed

- Keeps `logs/runtime_analytics.csv` focused on trend-friendly scalar and compact JSON fields.
- Removes the very large `bna_provenance_json` blob from future CSV rows.
- Adds full forensic snapshots to `logs/runtime_analytics_details.ndjson`, one JSON object per run.
- Keeps `logs/runtime_analytics_latest.json` as the latest full forensic snapshot.
- Adds BNA persistence/stability metrics:
  - `bna_repeated_from_previous_count`
  - `bna_max_consecutive_runs`
  - `bna_stuck_3plus_count`
  - per-BNA `consecutive_bna_runs`
  - per-BNA `seen_in_previous_run`
- Preserves read-only behavior:
  - no Notion writes
  - no ranking changes
  - no evaluator changes
  - no authority impact

## Files changed

- `core/runtime_analytics.py`
- `execution_engine_v2.py` hook marker only

## Outputs

- `logs/runtime_analytics.csv`
- `logs/runtime_analytics_latest.json`
- `logs/runtime_analytics_details.ndjson`

## Review commands

```bash
grep -A60 "AIOS RUNTIME ANALYTICS SUMMARY" test_run.log
tail -n 5 logs/runtime_analytics.csv
cat logs/runtime_analytics_latest.json
tail -n 3 logs/runtime_analytics_details.ndjson
```
