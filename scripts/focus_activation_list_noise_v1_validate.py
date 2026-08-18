from pathlib import Path
api = Path("aios/api/app.py").read_text()

checks = [
    ("open task query includes generated provenance",
     '"is_quick_win,is_just_do_it,created_at,updated_at,generated_source,task_role"' in api),
    ("focus activation generated_source excluded",
     'row.get("generated_source") != "focus_activation"' in api),
    ("focus activation task_role excluded",
     'row.get("task_role") != "focus_activation"' in api),
    ("filter happens before task_ids/state enrichment",
     api.index('rows = [') < api.index('task_ids = [row.get("id") for row in rows')),
]
failed = False
for label, ok in checks:
    print(("PASS" if ok else "FAIL") + f": {label}")
    failed |= not ok
if failed:
    raise SystemExit("RESULT: FOCUS ACTIVATION LIST NOISE V1 VALIDATION FAILED")
print("RESULT: FOCUS ACTIVATION LIST NOISE V1 STRUCTURE VALID")
