from pathlib import Path

root = Path(__file__).resolve().parents[1]
api = (root / 'aios/api/app.py').read_text()
start = api.index('def update_project_task_list_http')
end = api.index('@app.get("/projects/{project_id}"', start)
block = api[start:end]

# Regression: bulk project editing must write the submitted title and must not
# immediately launch a processor that can re-import an older legacy title.
assert '{"title": title, "project_order": order, "updated_at": now}' in block
assert '_request_processor_run()' not in block

print('Submitted existing-task title is written: PASS')
print('Immediate processor title race removed: PASS')
print('RESULT: PROJECT TASK RENAME AUTHORITY V1 SMOKE TEST PASSED')
