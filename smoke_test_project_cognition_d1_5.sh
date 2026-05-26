#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON="./venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
fi
$PYTHON -m py_compile scripts/aios_project_affinity_report.py core/project_cognition/historical_affinity.py
$PYTHON scripts/aios_project_affinity_report.py --help >/dev/null
$PYTHON - <<'PY'
from core.project_cognition.historical_affinity import HistoricalTask, summarize_historical_affinity
project_id='11111111-1111-1111-1111-111111111111'
tasks=[
    HistoricalTask(id='h1', title='Teach pizza workshop', done=True, project_ids=(project_id,)),
    HistoricalTask(id='h2', title='Move workshop bins', done=True, project_ids=(project_id,)),
    HistoricalTask(id='a1', title='Send bread message to community', done=False),
    HistoricalTask(id='a2', title='Unpack workshop bins', done=False),
]
summary=summarize_historical_affinity(tasks, project_name_by_id={project_id:'Workshops and Teaching'})
previews=summary.active_task_previews
assert any(p['task_title']=='Unpack workshop bins' for p in previews), previews
assert not any(p['task_title']=='Send bread message to community' and p['confidence']=='high' for p in previews), previews
print('D1.5 smoke test passed: weak-term weighting and broad one-word suppression active.')
PY
