#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
api = (root / "aios/api/app.py").read_text()
ast.parse(api)

checks = [
    ("v1.3 marker", 'AIOS_WEB_DASHBOARD_POPULATION_VERSION = "v1.3-full-open-population"' in api),
    ("no pre-section source slice", "rows = rows[:safe_limit]" not in api),
    ("Top 5 still capped", "top5 = take(sorted(rows, key=score_key), 5)" in api),
    ("Quick Wins still capped", "quick_wins = take(" in api and "key=quick_win_key" in api),
    ("Today remains section-selected", "today_items = take(" in api),
    ("JDI remains section-selected", "jdi_items = take(" in api),
    ("dedupe preserved", 'used: set[str] = set()' in api),
]
for label, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + label)
if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: FULL POPULATION FIX VALIDATION FAILED")
print("RESULT: FULL POPULATION FIX STRUCTURE VALID")
