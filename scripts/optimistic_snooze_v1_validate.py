from pathlib import Path

s = Path("aios/web_capture/app.py").read_text()

checks = [
    ("version marker", 'WEB_OPTIMISTIC_SNOOZE_VERSION = "optimistic-snooze-v2"' in s),
    ("JSON snooze endpoint", '@app.post("/tasks/{task_id}/snooze-optimistic")' in s),
    ("uses existing snooze helper", "_snooze_task(task_id, preset, custom_date)" in s),
    ("async snooze interception", 'form.addEventListener("submit", async (event)' in s),
    ("snooze fetch endpoint", '/snooze-optimistic`' in s),
    ("immediate task hide", 'node.classList.add("optimistic-hidden")' in s),
    ("project task row support", 'closest(".project-editor-row")' in s),
    ("BNA pending feedback", "Finding your next focus…" in s),
    ("failed snooze restores task", 'node.classList.remove("optimistic-hidden")' in s),
    ("failed snooze feedback", '"Task could not be snoozed."' in s),
]

failed = False
for label, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + label)
    failed = failed or not ok

if failed:
    raise SystemExit(1)

print("RESULT: OPTIMISTIC SNOOZE V1 STRUCTURE VALID")
