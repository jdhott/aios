from pathlib import Path

api = Path("aios/api/app.py").read_text()
web = Path("aios/web_capture/app.py").read_text()

checks = [
    ("non-focus completion helper", "def _refresh_non_focus_completion_after_action(" in api),
    ("non-focus skips processor", "task_list_refresh_scheduled" in api),
    ("shared focus rank helper", "def _task_is_dashboard_focus(" in api),
    ("non-focus delete skips processor", "was_dashboard_focus" in api.split("def delete_task_http")[1]),
    ("delete processor removed from else", "def delete_task_http" in api and '_request_processor_run()\n        except Exception:\n            pass' not in api.split("def delete_task_http")[1]),
    ("web task list poll after complete", "refreshTaskGroupsAfterComplete" in web),
    ("web summary pending poll loop", "refreshTaskGroupsAfterComplete" in web and "summary_pending" in web),
    ("web delete refreshes list", "refreshTaskGroupsOnce();" in web.split("delete-optimistic")[1]),
    ("optimistic complete v3", 'WEB_OPTIMISTIC_COMPLETE_VERSION = "optimistic-complete-v3"' in web),
    ("dashboard tasks poll v2", 'WEB_DASHBOARD_TASKS_POLL_VERSION = "dashboard-tasks-poll-v2"' in web),
]

for label, ok in checks:
    assert ok, f"FAIL: {label}"
    print(f"PASS: {label}")

print("RESULT: NON-FOCUS FAST PATH V1 STRUCTURE VALID")
