#!/usr/bin/env python3
from pathlib import Path
import ast
root = Path(__file__).resolve().parents[1]
web = (root / "aios/web_capture/app.py").read_text()
ast.parse(web)
checks = [
    ("dashboard v1.4 marker", 'WEB_DASHBOARD_UI_VERSION = "dashboard-v1.4-compact-capture-toggle"' in web),
    ("Dashboard title", '<h1 class="brand">Dashboard</h1>' in web),
    ("global Brain Dump sheet", 'id="brain-dump-sheet-root"' in web),
    ("capture fab", 'id="brain-dump-open"' in web),
    ("bullet parser", "if clean[:1] in {\"•\", \"-\", \"*\"}" in web),
    ("collapsible sections", '<details class="task-group"' in web),
    ("expand all", 'id="expandAllSections"' in web),
    ("collapse all", 'id="collapseAllSections"' in web),
    ("Projects nav retained", 'href="/projects"' in web),
    ("New Task nav retained", 'href="/tasks/new"' in web),
]
for label, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + label)
if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: DASHBOARD V1.4 VALIDATION FAILED")
print("RESULT: DASHBOARD V1.4 STRUCTURE VALID")
