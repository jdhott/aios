#!/usr/bin/env python3
from pathlib import Path
import ast
root = Path(__file__).resolve().parents[1]
web = (root / 'aios/web_capture/app.py').read_text()
ast.parse(web)
checks = [
    ('BNA marker', 'WEB_DASHBOARD_BNA_VERSION = "dashboard-bna-v1"' in web),
    ('rank selection', 'ranked_tasks.sort(key=lambda pair: pair[0])' in web),
    ('single BNA card', 'class="bna-card"' in web),
    ('BNA label', '⭐ Best Next Action' in web),
    ('Why now', 'Why now' in web),
    ('Open task', 'Open task →' in web),
]
for label, ok in checks:
    print(('PASS' if ok else 'FAIL') + ': ' + label)
if not all(ok for _, ok in checks):
    raise SystemExit('RESULT: DASHBOARD BNA V1 VALIDATION FAILED')
print('RESULT: DASHBOARD BNA V1 STRUCTURE VALID')
