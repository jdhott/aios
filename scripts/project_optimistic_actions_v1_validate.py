from pathlib import Path

web = Path("aios/web_capture/app.py").read_text()

checks = [
    ("projects version bump", 'WEB_PROJECTS_VERSION = "projects-v1.1-optimistic-actions"' in web),
    ("shared optimistic script helper", "def _optimistic_task_actions_script" in web),
    ("project surface script", '_optimistic_task_actions_script(surface="project")' in web),
    ("project complete forms", 'class="complete-form" data-task-id=' in web),
    ("project delete buttons", 'type="button" data-aios-delete="1"' in web),
    ("project inline snooze", 'css_class="project-task-snooze"' in web),
    ("no external project snooze forms", "external_form_id=snooze_form_id" not in web),
    ("project undo toast support", 'showOptimisticToast(state, "Task deleted")' in web),
    ("project row cleanup after undo window", "state.hiddenNodes.forEach((node) => node.remove());" in web),
    ("new task local trash only", "Remove unsaved task" in web),
]

for label, ok in checks:
    assert ok, f"FAIL: {label}"
    print(f"PASS: {label}")

print("RESULT: PROJECT OPTIMISTIC ACTIONS V1 STRUCTURE VALID")
