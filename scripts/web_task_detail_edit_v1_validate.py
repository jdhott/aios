#!/usr/bin/env python3
from pathlib import Path
import ast
root = Path(__file__).resolve().parents[1]
api = (root / "aios/api/app.py").read_text()
web = (root / "aios/web_capture/app.py").read_text()
ast.parse(api); ast.parse(web)
checks = [
    ("API marker", 'AIOS_TASK_DETAIL_EDIT_VERSION = "task-detail-edit-v1"' in api),
    ("GET task detail", '@app.get("/tasks/{task_id}"' in api),
    ("PATCH task detail", '@app.patch("/tasks/{task_id}"' in api),
    ("web marker", 'WEB_TASK_DETAIL_EDIT_VERSION = "task-detail-edit-v1"' in web),
    ("task links", 'class="task-link"' in web),
    ("detail page", "def _task_detail_page(" in web),
    ("edit route", '@app.post("/tasks/{task_id}/edit")' in web),
]
for label, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + label)
if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: TASK DETAIL/EDIT V1 VALIDATION FAILED")
print("RESULT: TASK DETAIL/EDIT V1 STRUCTURE VALID")
