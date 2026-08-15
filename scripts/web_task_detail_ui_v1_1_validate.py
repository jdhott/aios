#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
web = (root / "aios/web_capture/app.py").read_text()
ast.parse(web)

checks = [
    ("v1.1 marker", 'WEB_TASK_DETAIL_UI_VERSION = "task-detail-ui-v1.1-return-to-list"' in web),
    ("Back to Tasks removed", '← Back to Tasks' not in web),
    ("Cancel returns to list", '<a class="secondary-link" href="/">Cancel</a>' in web),
    ("Save returns to list", 'url="/?message=Task+updated."' in web),
    ("edit endpoint preserved", 'action="/tasks/{task_id}/edit"' in web),
]

for label, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + label)

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: TASK DETAIL UI V1.1 VALIDATION FAILED")

print("RESULT: TASK DETAIL UI V1.1 STRUCTURE VALID")
