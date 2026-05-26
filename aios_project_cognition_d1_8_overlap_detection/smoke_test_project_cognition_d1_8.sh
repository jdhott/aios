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

pool_a = "11111111-1111-1111-1111-111111111111"
pool_b = "33333333-3333-3333-3333-333333333333"
house_id = "22222222-2222-2222-2222-222222222222"

tasks = [
    HistoricalTask(id="h1", title="Check skimmer basket in pool", done=True, project_ids=(pool_a,)),
    HistoricalTask(id="h2", title="Brush pool and add chlorine", done=True, project_ids=(pool_a,)),
    HistoricalTask(id="h3", title="Organize pool equipment", done=True, project_ids=(pool_a,)),
    HistoricalTask(id="h4", title="Test pool chlorine and clean filter", done=True, project_ids=(pool_b,)),
    HistoricalTask(id="h5", title="Vacuum pool and check skimmer", done=True, project_ids=(pool_b,)),
    HistoricalTask(id="h6", title="Move pool vacuum equipment", done=True, project_ids=(pool_b,)),
    HistoricalTask(id="h7", title="Organize equipment in storage", done=True, project_ids=(house_id,)),
    HistoricalTask(id="h8", title="Move storage equipment to basement", done=True, project_ids=(house_id,)),
    HistoricalTask(id="h9", title="Clean basement storage area", done=True, project_ids=(house_id,)),
    HistoricalTask(id="a1", title="Organize pool equipment for opening"),
    HistoricalTask(id="a2", title="Send bread app message"),
]
summary = summarize_historical_affinity(
    tasks,
    project_name_by_id={
        pool_a: "Pool Opening and Maintenance",
        pool_b: "Pool Maintenance and Operations",
        house_id: "Household Storage",
    },
)
lines = "\n".join(summary.telemetry_lines())
assert "D1.8" in lines, lines
assert "Project overlap detection: enabled=true" in lines, lines
assert "Overlapping project neighborhoods:" in lines, lines
overlap = next((o for o in summary.overlapping_neighborhoods if "Pool Opening" in o["left_label"] + o["right_label"] and "Pool Maintenance" in o["left_label"] + o["right_label"]), None)
assert overlap is not None, summary.overlapping_neighborhoods
assert overlap["risk"] in {"medium", "high"}, overlap
pool = next((p for p in summary.active_task_previews if "pool equipment" in p["task_title"]), None)
assert pool is not None, summary.active_task_previews
assert pool["confidence"] == "high", pool
assert all("bread app" not in p["task_title"].lower() for p in summary.active_task_previews), summary.active_task_previews
print("D1.8 smoke test passed: overlap detection enabled; runner-up ambiguity retained; writes=0")
PY
