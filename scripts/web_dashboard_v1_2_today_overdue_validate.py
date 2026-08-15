#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
api = (root / "aios/api/app.py").read_text()
ast.parse(api)

checks = [
    ("marker", 'AIOS_WEB_DASHBOARD_TODAY_VERSION = "v1.2-today-includes-overdue"' in api),
    ("naive dates include overdue", "dt.date() <= today" in api),
    ("timezone-aware dates include overdue", "dt.astimezone(toronto).date() <= today" in api),
    ("fallback includes overdue", "str(raw)[:10] <= today.isoformat()" in api),
    ("Today still uses due_today", "if due_today(row)" in api),
]

for label, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + label)

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: TODAY + OVERDUE VALIDATION FAILED")

print("RESULT: TODAY + OVERDUE STRUCTURE VALID")
