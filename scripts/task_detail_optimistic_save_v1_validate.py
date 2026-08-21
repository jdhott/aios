#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
web = (root / "aios/web_capture/app.py").read_text()
ast.parse(web)

checks = [
    ("web marker", 'WEB_TASK_DETAIL_OPTIMISTIC_SAVE_VERSION = "task-detail-async-save-v4"' in web),
    ("await save before navigate", "await fetch(saveUrl" in web),
    ("optimistic save route", '@app.post("/tasks/{task_id}/edit-optimistic")' in web),
    ("sync api save", "def edit_task_optimistic_web(" in web and "_update_task_detail(task_id, payload)" in web),
    ("save error surfaced to client", 'payload.error' in web and 'id="taskSaveNotice"' in web),
    ("success flash on return", '"aios-flash"' in web and "Task saved." in web),
    ("client flash reader", "def _client_flash_script(" in web),
    ("edit redirects with saved message", "def _return_with_task_save_message(" in web),
    ("task detail no-store", '"Cache-Control": "no-store"' in web),
    ("async save marker on form", 'data-async-save="' in web),
    ("defer datetime-local", 'type="datetime-local" name="defer_until"' in web),
    ("fast return helper", "def _with_fast_return_param(" in web),
    ("dashboard fast shell", 'request.query_params.get("fast") == "1"' in web),
]

for label, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + label)
if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: TASK DETAIL ASYNC SAVE V4 VALIDATION FAILED")
print("RESULT: TASK DETAIL ASYNC SAVE V4 STRUCTURE VALID")
