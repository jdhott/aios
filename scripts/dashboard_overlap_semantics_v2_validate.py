#!/usr/bin/env python3
from pathlib import Path

api = Path('aios/api/app.py').read_text()
checks = [
    ('Top 5 remains ranks 2 through 6', '2 <= int(row.get("execution_rank")) <= 6' in api),
    ('Today remains independent', '[row for row in rows if due_today(row)]' in api),
    ('JDI remains independent', '[row for row in rows if bool(row.get("is_just_do_it"))]' in api),
    ('Quick Wins builds stronger-section exclusion set', 'stronger_ids = {str(row.get("id")) for row in top5 + today_items + jdi_items}' in api),
    ('Quick Wins excludes stronger sections', 'and str(row.get("id")) not in stronger_ids' in api),
    ('Quick Wins still excludes BNA flag', 'and not bool(row.get("best_next_action"))' in api),
    ('Quick Wins still excludes rank 1', 'and row.get("execution_rank") != 1' in api),
]
failed=[]
for label, ok in checks:
    print(('PASS' if ok else 'FAIL') + ': ' + label)
    if not ok: failed.append(label)
if failed:
    print('RESULT: DASHBOARD OVERLAP SEMANTICS V2 VALIDATION FAILED')
    raise SystemExit(1)
print('RESULT: DASHBOARD OVERLAP SEMANTICS V2 STRUCTURE VALID')
