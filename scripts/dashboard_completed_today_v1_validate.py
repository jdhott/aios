from pathlib import Path

api = Path('aios/api/app.py').read_text()
web = Path('aios/web_capture/app.py').read_text()

checks = [
    ('completed today queries completed tasks', '.eq("is_done", True)' in api and 'completed_at' in api),
    ('uses Toronto local day boundaries', 'local_start = datetime.combine(today' in api and 'America/Toronto' in api),
    ('completed list has no count cap', 'completed_today = [' in api and 'completed_rows' in api),
    ('focus activation helpers excluded', 'generated_source") != "focus_activation"' in api),
    ('completed tasks sorted newest first', '.order("completed_at", desc=True)' in api),
    ('completed today section returned', '"completed_today": completed_today' in api),
    ('web exposes completed today', '("Completed Today", "completed_today")' in web),
    ('completed rows support actions', 'data-aios-uncomplete' in web and 'completed-task-row' in web),
    ('completed titles link to task detail', 'href="/tasks/{task_id}"' in web),
]
failed = []
for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")
    if not ok:
        failed.append(label)
if failed:
    raise SystemExit('RESULT: DASHBOARD COMPLETED TODAY V1 STRUCTURE VALIDATION FAILED')
print('RESULT: DASHBOARD COMPLETED TODAY V1 STRUCTURE VALID')
