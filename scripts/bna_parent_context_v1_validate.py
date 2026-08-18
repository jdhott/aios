from pathlib import Path
api=Path('aios/api/app.py').read_text()
web=Path('aios/web_capture/app.py').read_text()
checks=[
 ('focus API selects parent task id', 'project_id,parent_task_id,is_quick_win' in api),
 ('focus API resolves parent title', 'task["parent_title"]' in api and '.eq("id", parent_id)' in api),
 ('BNA renders parent metadata', 'focus-parent-meta' in web and 'Part of: ' in web),
 ('BNA parent link is clickable', 'href="/tasks/{html.escape(focus_parent_id, quote=True)}"' in web),
 ('Start Here does not render parent metadata', 'focus-start-parent-meta' not in web),
 ('BNA title font reduced', 'font-size:1.08rem' in web),
]
for label,ok in checks:
 print(('PASS' if ok else 'FAIL')+': '+label)
assert all(ok for _,ok in checks)
print('RESULT: BNA PARENT CONTEXT V1 STRUCTURE VALID')
