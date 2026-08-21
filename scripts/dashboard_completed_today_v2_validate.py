from pathlib import Path

api = Path("aios/api/app.py").read_text()
web = Path("aios/web_capture/app.py").read_text()

checks = [
    ("completed today API section", '"completed_today": completed_today' in api),
    ("open task section order excludes completed", "_HOME_OPEN_TASK_SECTION_KEYS" in web),
    ("completed panel is separate from task groups", 'id="completed-today-panel"' in web),
    ("completed panel hidden by default", 'id="completed-today-panel" hidden' in web),
    ("dashboard tasks API returns completed_html", '"completed_html"' in web),
    ("no dashboard completed summary block", "completed-today-summary-label" not in web),
    ("completed rows support uncomplete", "data-aios-uncomplete" in web),
    ("completed rows support delete", "completed-task-row" in web and "data-aios-delete" in web),
    ("show all reveals completed panel", "homeCompletedVisible" in web),
    ("progressive section order is open tasks only", '"completedSectionKey"' in web),
]
failed = []
for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")
    if not ok:
        failed.append(label)
if failed:
    raise SystemExit("RESULT: DASHBOARD COMPLETED TODAY V2 VALIDATION FAILED")
print("RESULT: DASHBOARD COMPLETED TODAY V2 VALID")
