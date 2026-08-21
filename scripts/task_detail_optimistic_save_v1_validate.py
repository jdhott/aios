#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
web = (root / "aios/web_capture/app.py").read_text()
ast.parse(web)

checks = [
    ("web marker", 'WEB_TASK_DETAIL_OPTIMISTIC_SAVE_VERSION = "task-detail-async-save-v3"' in web),
    ("instant client navigation", "window.history.back()" in web and "keepalive: true" in web),
    ("background helper", "def _save_task_detail_background(" in web),
    ("edit uses background tasks", "background_tasks.add_task(_save_task_detail_background" in web),
    ("edit redirects without blocking api", "def edit_task_web(" in web and "background_tasks: BackgroundTasks" in web),
    ("optimistic route accepts async", '@app.post("/tasks/{task_id}/edit-optimistic")' in web),
    ("task detail no-store", '"Cache-Control": "no-store"' in web),
    ("async save marker on form", 'data-async-save="' in web),
    ("defer datetime-local", 'type="datetime-local" name="defer_until"' in web),
    ("fast return helper", "def _with_fast_return_param(" in web),
    ("dashboard fast shell", 'request.query_params.get("fast") == "1"' in web),
]

for label, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + label)
if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: TASK DETAIL ASYNC SAVE V2 VALIDATION FAILED")
print("RESULT: TASK DETAIL ASYNC SAVE V2 STRUCTURE VALID")
