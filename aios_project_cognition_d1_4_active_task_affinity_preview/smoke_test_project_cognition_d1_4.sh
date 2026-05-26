#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
PYTHON="${PYTHON:-./venv/bin/python}"
if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
fi

$PYTHON -m py_compile scripts/aios_project_affinity_report.py core/project_cognition/historical_affinity.py
$PYTHON scripts/aios_project_affinity_report.py --help >/dev/null
$PYTHON - <<'PY'
from core.project_cognition.historical_affinity import HistoricalTask, summarize_historical_affinity

project_id = "35e1faccc5ab81bd9b6cf6953c15f0b3"
tasks = [
    HistoricalTask(id="1", title="Brush pool skimmer basket", done=True, project_ids=(project_id,)),
    HistoricalTask(id="2", title="Move pool chemicals to shed", done=True, project_ids=(project_id,)),
    HistoricalTask(id="3", title="Clean pool filter basket", done=False),
    HistoricalTask(id="4", title="Bake oatmeal molasses bread", done=True, suggested_project="Weekly Bakery Production"),
    HistoricalTask(id="5", title="Package bread bags", done=False),
]
summary = summarize_historical_affinity(tasks, project_name_by_id={
    "35e1facc-c5ab-81bd-9b6c-f6953c15f0b3": "Pool Maintenance and Operations"
})
lines = "\n".join(summary.telemetry_lines())
assert "Pool Maintenance and Operations" in lines, lines
assert "Active affinity preview" in lines, lines
assert "Clean pool filter basket" in lines, lines
assert "writes=0" in lines, lines
assert "execution_authority_impact=none" in lines, lines
print("D1.4 smoke test passed: active-task affinity preview is read-only and project names resolve.")
PY
