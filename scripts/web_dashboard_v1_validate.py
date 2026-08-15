#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
api = (root / "aios/api/app.py").read_text()
web = (root / "aios/web_capture/app.py").read_text()
ast.parse(api)
ast.parse(web)

checks = [
    ("Top 5 section", '"top5": top5' in api),
    ("Quick Wins section", '"quick_wins": quick_wins' in api),
    ("Today section", '"today": today_items' in api),
    ("JDI section", '"just_do_it": jdi_items' in api),
    ("dedupe precedence", 'used: set[str] = set()' in api),
    ("Top 5 score sort", 'top5 = take(sorted(rows, key=score_key), 5)' in api),
    ("Quick Wins importance sort", 'importance_order = {' in api and 'key=quick_win_key' in api),
    ("Toronto today calculation", 'ZoneInfo("America/Toronto")' in api),
    ("Today uses due_at", 'if due_today(row)' in api),
    ("web Top 5 heading", '("Top 5", "top5")' in web),
    ("web Quick Wins heading", '("Quick Wins", "quick_wins")' in web),
    ("web Today heading", '("Today", "today")' in web),
    ("web JDI heading", '("Just Do It", "just_do_it")' in web),
    ("checkbox/trash preserved", 'complete-checkbox' in web and 'trash-button' in web),
]
for label, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + label)
if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: AIOS WEB DASHBOARD V1 VALIDATION FAILED")
print("RESULT: AIOS WEB DASHBOARD V1 STRUCTURE VALID")
