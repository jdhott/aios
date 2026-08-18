from pathlib import Path

api = Path("aios/api/app.py").read_text()
web = Path("aios/web_capture/app.py").read_text()

checks = [
    ("parent due date fetched", '.select("id,title,due_at")' in api),
    ("effective due date assigned", 'row["effective_due_at"] = parent_due_at' in api),
    ("inheritance flagged", 'row["due_inherited_from_parent"] = True' in api),
    ("child due overrides parent", 'row["effective_due_at"] = row.get("due_at")' in api),
    ("Today uses effective due date", 'raw = row.get("effective_due_at") or row.get("due_at")' in api),
    ("Today ordering uses effective due date", 'row.get("effective_due_at") or row.get("due_at")' in api),
    ("web displays effective due date", 'task.get("effective_due_at") or task.get("due_at")' in web),
]

failed = False
for label, ok in checks:
    print(("PASS" if ok else "FAIL") + f": {label}")
    failed |= not ok

if failed:
    raise SystemExit("RESULT: BREAKDOWN DUE-DATE INHERITANCE V1 VALIDATION FAILED")
print("RESULT: BREAKDOWN DUE-DATE INHERITANCE V1 STRUCTURE VALID")
