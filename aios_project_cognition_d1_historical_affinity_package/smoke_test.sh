#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-$PWD}"
cd "$ROOT"
PYTHON="${PYTHON:-./venv/bin/python}"
if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
fi
"$PYTHON" - <<'PY'
from core.project_cognition.historical_affinity import HistoricalTask, summarize_historical_affinity
sample = [
    HistoricalTask(id='1', title='Open pool and test chlorine', done=True, project_ids=('pool',)),
    HistoricalTask(id='2', title='Clean pool filter basket', done=True, project_ids=('pool',)),
    HistoricalTask(id='3', title='Book dentist appointment', done=False),
]
summary = summarize_historical_affinity(sample)
assert summary.historical_tasks == 2
assert summary.project_groups == 1
print('\n'.join(summary.telemetry_lines()))
PY
