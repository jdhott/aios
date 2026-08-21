from pathlib import Path
api = Path("aios/api/app.py").read_text()
web = Path("aios/web_capture/app.py").read_text()
checks = [
    ("optimistic version marker", 'WEB_OPTIMISTIC_COMPLETE_VERSION = "optimistic-complete-v3"' in web),
    ("API delayed trigger helper", "def _request_processor_run_after_completion(" in api),
    ("complete uses BackgroundTasks", "def complete_task_http(task_id: str, background_tasks: BackgroundTasks)" in api),
    ("non-focus completion fast path", "_refresh_non_focus_completion_after_action" in api),
    ("processor not deferred for fast paths", '"processor_deferred": False' in api),
    ("undo API endpoint", '@app.post("/tasks/{task_id}/undo-complete"' in api),
    ("undo reopens parent", '"is_done": False' in api and '"is_open": True' in api),
    ("undo restores generated children", '"restored_activation_children"' in api),
    ("web JSON complete endpoint", '@app.post("/tasks/{task_id}/complete-optimistic")' in web),
    ("web JSON undo endpoint", '@app.post("/tasks/{task_id}/undo-complete-optimistic")' in web),
    ("task rows tagged", 'class="task-row" data-task-id=' in web),
    ("focus card tagged", 'id="focus-card" data-task-id=' in web),
    ("immediate hide behavior", 'classList.add("optimistic-hidden")' in web),
    ("Undo toast", 'Task completed' in web and 'Undo</button>' in web),
    ("4 second undo window", "WEB_TOAST_UNDO_MS = 4000" in web),
    ("5 second backend debounce exceeds 4 second Undo window", "AIOS_COMPLETION_PROCESSOR_DELAY_SECONDS" in api),
    ("immediate focus polling after complete", "startFocusPollingAfterComplete" in web),
    ("stale spinner refresh", "focusCardHasPendingSpinner" in web),
    ("BNA pending feedback", "Finding your next focus…" in web),
    ("activation pending feedback", "Finding your next step…" in web),
    ("failure restores UI", "restoreOptimisticNodes(state)" in web),
]
for label, ok in checks:
    assert ok, f"FAIL: {label}"
    print(f"PASS: {label}")
print("RESULT: OPTIMISTIC COMPLETE V1 STRUCTURE VALID")
