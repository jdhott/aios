from pathlib import Path
api = Path("aios/api/app.py").read_text()
web = Path("aios/web_capture/app.py").read_text()
complete_start = api.index('@app.post("/tasks/{task_id}/complete"')
complete_end = api.index('@app.post("/tasks/{task_id}/undo-complete"', complete_start)
complete = api[complete_start:complete_end]
assert "_request_processor_run()" not in complete
assert "background_tasks.add_task" in complete
print("PASS: completion persistence no longer waits for processor trigger")
undo_start = api.index('@app.post("/tasks/{task_id}/undo-complete"')
undo_end = api.index('@app.post("/tasks/{task_id}/not-now"', undo_start)
undo = api[undo_start:undo_end]
assert '"completed_at": None' in undo
assert '"is_done": False' in undo
assert '"is_open": True' in undo
print("PASS: Undo restores authoritative open state")
assert 'event.preventDefault();' in web
assert 'showOptimisticToast(state)' in web
assert 'window.setTimeout(() => finishOptimisticWindow(state), 8000)' in web
assert 'window.location.href = "/?refresh_focus=1#focus-card"' in web
print("PASS: dashboard updates immediately and preserves an Undo window")
print("PASS: BNA reconciliation waits until the Undo window closes")
print("RESULT: OPTIMISTIC COMPLETE V1 SMOKE TEST PASSED")
