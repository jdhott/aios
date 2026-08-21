from pathlib import Path

web = Path("aios/web_capture/app.py").read_text()
api = Path("aios/api/app.py").read_text()

checks = [
    ("optimistic delete version", 'WEB_OPTIMISTIC_DELETE_VERSION = "optimistic-delete-v1"' in web),
    ("delete JSON endpoint", '@app.post("/tasks/{task_id}/delete-optimistic")' in web),
    ("delete prevents navigation", "delete-optimistic" in web and "event.preventDefault()" in web),
    ("delete hides rows immediately", 'classList.add("optimistic-hidden")' in web),
    ("delete confirm in JS", 'window.confirm("Delete this task?")' in web),
    ("delete restores on failure", "Task could not be deleted." in web),
    ("delete forms tagged", 'class="delete-form" data-task-id=' in web),
    ("dashboard delete uses data-task-id", 'delete-form" data-task-id=' in web),
    ("focus delete fast path", "was_dashboard_focus" in api and "_refresh_dashboard_focus_after_action" in api),
]

for label, ok in checks:
    assert ok, f"FAIL: {label}"
    print(f"PASS: {label}")

print("RESULT: OPTIMISTIC DELETE V1 STRUCTURE VALID")
