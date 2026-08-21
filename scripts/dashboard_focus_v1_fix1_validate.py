#!/usr/bin/env python3
from pathlib import Path
import ast
web = Path("aios/web_capture/app.py").read_text()
ast.parse(web)
s = web.find("def _page(")
e = web.find("\n\n@app.get(", s)
page = web[s:e]
checks = [
    ("fix marker", 'WEB_DASHBOARD_FOCUS_FIX_VERSION = "dashboard-focus-v1-fix2"' in web),
    ("focus_id early init", 'focus_id = str(focus.get("id") or "") if focus else ""' in page),
    ("rank1 filtering retained", "if focus_id:" in page),
    ("focus card retained", 'class="focus-card"' in page),
]
for label, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + label)
if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: DASHBOARD FOCUS V1 FIX1 VALIDATION FAILED")
print("RESULT: DASHBOARD FOCUS V1 FIX1 STRUCTURE VALID")
