#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
web = (root / "aios/web_capture/app.py").read_text()
ast.parse(web)

checks = [
    ("async save v4 marker", 'WEB_TASK_DETAIL_OPTIMISTIC_SAVE_VERSION = "task-detail-async-save-v4"' in web),
    ("optimistic save endpoint", '@app.post("/tasks/{task_id}/edit-optimistic")' in web),
    ("sync save on optimistic route", "def edit_task_optimistic_web(" in web and '"ok": True' in web),
    ("save error helper", "def _task_save_user_error(" in web),
    ("return success message helper", "def _return_with_task_save_message(" in web),
    ("client flash script", "def _client_flash_script(" in web),
    ("session flash storage", '"aios-flash"' in web and "Task saved." in web),
    ("save button saving state", 'submitButton.textContent = active ? "Saving…"' in web),
    ("inline save error host", 'id="taskSaveNotice"' in web),
    ("await fetch before navigate", "await fetch(saveUrl" in web),
    ("no background task save", "_save_task_detail_background" not in web),
]

for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: TASK DETAIL SAVE FEEDBACK V1 VALIDATION FAILED")

print("RESULT: TASK DETAIL SAVE FEEDBACK V1 STRUCTURE VALID")
