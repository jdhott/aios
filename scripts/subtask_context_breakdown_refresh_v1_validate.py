from pathlib import Path
api = Path('aios/api/app.py').read_text()
web = Path('aios/web_capture/app.py').read_text()
checks = [
    ('dashboard task query carries parent identity', 'parent_task_id' in api and 'id,title,status,due_at,defer_until,project_id,importance,parent_task_id' in api),
    ('parent titles are enriched from Supabase', 'parent_title_by_id' in api and 'row["parent_title"]' in api),
    ('child title remains presentation-independent', 'Part of:' in web and 'task-parent-meta' in web),
    ('parent title links to Task Detail', 'href="/tasks/{html.escape(parent_id, quote=True)}"' in web),
    ('manual breakdown pending state reloads', 'window.location.reload();' in web),
]
failed=[]
for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")
    if not ok: failed.append(label)
if failed:
    raise SystemExit('RESULT: SUBTASK CONTEXT + BREAKDOWN REFRESH V1 VALIDATION FAILED')
print('RESULT: SUBTASK CONTEXT + BREAKDOWN REFRESH V1 STRUCTURE VALID')
