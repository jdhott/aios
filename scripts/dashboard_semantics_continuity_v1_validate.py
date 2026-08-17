#!/usr/bin/env python3
from pathlib import Path
import ast
root = Path(__file__).resolve().parents[1]
api = (root / 'aios/api/app.py').read_text()
web = (root / 'aios/web_capture/app.py').read_text()
ast.parse(api); ast.parse(web)
checks = [
 ('Top 5 is ranks 2 through 6', '2 <= int(row.get("execution_rank")) <= 6' in api),
 ('Today is independent of precedence take()', 'today_items = sorted(' in api and '[row for row in rows if due_today(row)]' in api),
 ('Today may include focus task', 'if focus_id and key != "today"' in web),
 ('section state stored in browser', 'aios-dashboard-section-state-v1' in web and 'localStorage.setItem(sectionStateKey' in web),
 ('section state restored on load', 'restoreSectionState();' in web),
]
for label, ok in checks: print(('PASS' if ok else 'FAIL') + ': ' + label)
if not all(ok for _,ok in checks): raise SystemExit('RESULT: DASHBOARD SEMANTICS + CONTINUITY V1 VALIDATION FAILED')
print('RESULT: DASHBOARD SEMANTICS + CONTINUITY V1 STRUCTURE VALID')
