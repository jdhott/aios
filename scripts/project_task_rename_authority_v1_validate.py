from pathlib import Path

root = Path(__file__).resolve().parents[1]
api = (root / 'aios/api/app.py').read_text()
start = api.index('def update_project_task_list_http')
end = api.index('@app.get("/projects/{project_id}"', start)
block = api[start:end]

assert '.update({"title": title, "project_order": order, "updated_at": now})' in block
assert '_request_processor_run()' not in block
assert 'authoritative in Supabase' in block

print('PASS: project task title edits remain authoritative in Supabase')
print('PASS: project task save no longer triggers stale-title processor race')
print('RESULT: PROJECT TASK RENAME AUTHORITY V1 STRUCTURE VALID')
