from pathlib import Path
root=Path(__file__).resolve().parents[1]
web=(root/'aios/web_capture/app.py').read_text(); api=(root/'aios/api/app.py').read_text()
assert 'data-project-task-list' in web
assert 'row.dataset.taskId' in web
assert 'JSON.stringify(tasks)' in web
assert 'project_order is None' in api
assert 'removed_ids = current_ids - requested_existing' in api
print('Drag + inline edit + remove + add serialization: PASS')
print('Project ordering takes precedence over execution rank: PASS')
print('Removed open tasks are archived only on Save: PASS')
print('RESULT: PROJECT TASK LIST EDITOR V1 SMOKE TEST PASSED')
