#!/usr/bin/env python3
from pathlib import Path
import ast
web = Path("aios/web_capture/app.py").read_text()
ast.parse(web)
s = web.find("def _page(")
e = web.find("\n\n@app.get(", s)
page = web[s:e]
checks = [
    ("fix1 marker", 'WEB_DASHBOARD_BNA_VERSION = "dashboard-bna-v1-fix1"' in web),
    ("bna_card defined in _page", '    bna_card = ""' in page),
    ("rank selection in _page", "ranked_tasks.sort(key=lambda pair: pair[0])" in page),
    ("bna_card rendered", "{bna_card}" in page),
    ("BNA CSS", ".bna-card {{" in page),
]
for label, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + label)
if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: DASHBOARD BNA V1 FIX1 VALIDATION FAILED")
print("RESULT: DASHBOARD BNA V1 FIX1 STRUCTURE VALID")
