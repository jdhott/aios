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

pool_id = "11111111-1111-1111-1111-111111111111"
house_id = "22222222-2222-2222-2222-222222222222"

tasks = [
    HistoricalTask(id="h1", title="Check skimmer basket in pool", done=True, project_ids=(pool_id,)),
    HistoricalTask(id="h2", title="Brush pool and add chlorine", done=True, project_ids=(pool_id,)),
    HistoricalTask(id="h3", title="Organize pool equipment", done=True, project_ids=(pool_id,)),
    HistoricalTask(id="h4", title="Organize equipment in storage", done=True, project_ids=(house_id,)),
    HistoricalTask(id="h5", title="Move storage equipment to basement", done=True, project_ids=(house_id,)),
    HistoricalTask(id="h6", title="Clean basement storage area", done=True, project_ids=(house_id,)),
    HistoricalTask(id="a1", title="Organize pool equipment for opening"),
    HistoricalTask(id="a2", title="Send bread app message"),
]
summary = summarize_historical_affinity(
    tasks,
    project_name_by_id={pool_id: "Pool Opening and Maintenance", house_id: "Household Storage"},
)
lines = "\n".join(summary.telemetry_lines())
assert "D1.7" in lines, lines
assert "Runner-up ambiguity: enabled=true" in lines, lines
pool = next((p for p in summary.active_task_previews if "pool equipment" in p["task_title"]), None)
assert pool is not None, summary.active_task_previews
assert pool["confidence"] == "high", pool
assert "runner_up" in pool, pool
assert "ambiguity" in pool, pool
assert pool["runner_up"] is None or "project_label" in pool["runner_up"], pool
assert all("bread app" not in p["task_title"].lower() for p in summary.active_task_previews), summary.active_task_previews
print("D1.7 smoke test passed: runner-up ambiguity telemetry enabled; broad terms suppressed; writes=0")
PY
