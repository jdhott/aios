#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
web = (root / "aios/web_capture/app.py").read_text()
ast.parse(web)

checks = [
    ("UI marker", 'WEB_TASK_DETAIL_UI_VERSION = "task-detail-ui-v1"' in web),
    ("responsive two-column layout", 'grid-template-columns:minmax(0,1.35fr)' in web),
    ("mobile layout", '@media (max-width:760px)' in web),
    ("task details card", 'Task Details' in web),
    ("read-only AIOS panel", 'These values are calculated by AIOS' in web),
    ("save button", 'Save Changes' in web),
    ("cancel link", 'Cancel' in web),
    ("existing edit endpoint preserved", 'action="/tasks/{task_id}/edit"' in web),
]
for label, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + label)
if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: TASK DETAIL UI V1 VALIDATION FAILED")
print("RESULT: TASK DETAIL UI V1 STRUCTURE VALID")
