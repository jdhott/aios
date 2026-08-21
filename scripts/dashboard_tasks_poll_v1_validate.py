from pathlib import Path

web = Path("aios/web_capture/app.py").read_text()
dashboard_js = web.split("def _page(")[1].split("</html>")[0]

checks = [
    ("version marker", 'WEB_DASHBOARD_TASKS_POLL_VERSION = "dashboard-tasks-poll-v1"' in web),
    ("shared tasks view helper", "def _tasks_sections_view(" in web),
    ("tasks fingerprint helper", "def _tasks_sections_fingerprint(" in web),
    ("dashboard tasks JSON endpoint", '@app.get("/api/dashboard-tasks")' in web),
    ("task groups wrapper", 'id="dashboard-task-groups"' in web),
    ("tasks poll config injected", "window.__AIOS_DASHBOARD_TASKS__" in web),
    ("fetch-based tasks polling", 'new URL("/api/dashboard-tasks"' in web),
    ("parallel focus and tasks fetch", "Promise.all" in dashboard_js),
    ("partial task list replace", "replaceTaskGroups" in web),
    ("rebind after task patch", "initTaskList" in web),
    ("no snooze focus-change reload", "if (focusChanged) {\n                window.location.reload();" not in web),
    ("list snooze sync", "refreshTaskGroupsOnce()" in web),
    ("non-focus complete sync", "state.affectsFocus" in web and "refreshTaskGroupsOnce();" in web),
    ("summary pending keeps polling", "summary_pending" in web),
]

failed = False
for label, ok in checks:
    print(f'{"PASS" if ok else "FAIL"}: {label}')
    failed |= not ok

if failed:
    raise SystemExit("RESULT: DASHBOARD TASKS POLL V1 VALIDATION FAILED")
print("RESULT: DASHBOARD TASKS POLL V1 VALIDATION PASSED")
