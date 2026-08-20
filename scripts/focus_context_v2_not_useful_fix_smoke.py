from pathlib import Path
api=Path('aios/api/app.py').read_text()
web=Path('aios/web_capture/app.py').read_text()
start=api.index('@app.post("/tasks/{task_id}/not-useful"')
end=api.index('class TaskSnoozeRequest', start)
block=api[start:end]
assert '"is_open": False' not in block
assert '"activation_disposition": "not_useful"' in block
print('PASS: Not useful preserves current Start Here')
start=api.index('def save_focus_context_http')
end=api.index('@app.post("/tasks/{task_id}/delete"', start)
block=api[start:end]
assert '.eq("activation_disposition", "not_useful")' in block
assert '"is_open": False' in block
print('PASS: context save is retirement commit point')
assert 'Marked not useful' in web
assert '"" if focus_context_state in {"pending", "answer_pending", "ready"} else' in web
print('PASS: rejected reference remains and duplicate help action is hidden')
print('RESULT: FOCUS CONTEXT V2 NOT-USEFUL FIX SMOKE TEST PASSED')
