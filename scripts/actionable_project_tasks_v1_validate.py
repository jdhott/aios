from pathlib import Path
web = Path('aios/web_capture/app.py').read_text()
checks = [
 ('project tasks have completion forms', 'project-task-row' in web and 'name="return_to"' in web),
 ('project tasks reuse normal completion endpoint', 'action="/tasks/{task_id}/complete"' in web),
 ('project tasks reuse normal delete endpoint', 'action="/tasks/{task_id}/delete"' in web),
 ('project task title remains linked', 'class="project-task-link"' in web),
 ('project actions return to project task list', '#project-tasks' in web),
 ('global completion accepts return target', 'return_to: Annotated[str, Form()] = ""' in web),
]
failed=False
for label, ok in checks:
 print(('PASS' if ok else 'FAIL')+': '+label); failed |= not ok
print('RESULT: ACTIONABLE PROJECT TASKS V1 STRUCTURE ' + ('FAILED' if failed else 'VALID'))
raise SystemExit(1 if failed else 0)
