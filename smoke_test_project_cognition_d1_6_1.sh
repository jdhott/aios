#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
PYTHON_BIN="${PYTHON_BIN:-./venv/bin/python}"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="python3"
fi
"$PYTHON_BIN" -m py_compile core/project_cognition/historical_affinity.py scripts/aios_project_affinity_report.py
"$PYTHON_BIN" - <<'PY'
from core.project_cognition.historical_affinity import HistoricalTask, summarize_historical_affinity

tasks = [
    HistoricalTask(id="h1", title="Check skimmer basket in pool", done=True, project_ids=("11111111-1111-1111-1111-111111111111",)),
    HistoricalTask(id="h2", title="Brush pool and add chlorine", done=True, project_ids=("11111111-1111-1111-1111-111111111111",)),
    HistoricalTask(id="h3", title="Organize pool equipment", done=True, project_ids=("11111111-1111-1111-1111-111111111111",)),
    HistoricalTask(id="a1", title="Organize pool equipment for opening"),
    HistoricalTask(id="a2", title="Send bread app message"),
]
summary = summarize_historical_affinity(tasks, project_name_by_id={"11111111-1111-1111-1111-111111111111":"Pool Opening and Maintenance"})
lines = "\n".join(summary.telemetry_lines())
assert "D1.6.1" in lines, lines
assert "threshold=14" in lines, lines
pool = next((p for p in summary.active_task_previews if "pool equipment" in p["task_title"]), None)
assert pool is not None, summary.active_task_previews
assert pool["confidence"] == "high", pool
assert all("bread app" not in p["task_title"].lower() for p in summary.active_task_previews), summary.active_task_previews
print("D1.6.1 smoke test passed: anchor confidence threshold calibrated; broad terms suppressed; writes=0")
PY
