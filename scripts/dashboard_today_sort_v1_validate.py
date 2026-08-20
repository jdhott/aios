from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "aios" / "api" / "app.py"
text = APP.read_text()

checks = [
    ('AIOS_WEB_DASHBOARD_TODAY_VERSION = "v1.3-today-importance-due-sort"', "Today version marker"),
    ('def today_sort_key(row: dict):', "dedicated Today sort key"),
    ('importance_order.get(row.get("importance"), 99)', "importance is primary sort"),
    ('due_key,', "due datetime is secondary sort"),
    ('key=today_sort_key', "Today list uses new sort key"),
    ('*score_key(row)', "stable execution-score tie breaker"),
]

for needle, label in checks:
    if needle not in text:
        raise SystemExit(f"FAIL: {label}")
    print(f"PASS: {label}")

print("RESULT: DASHBOARD TODAY SORT V1 STRUCTURE VALID")
