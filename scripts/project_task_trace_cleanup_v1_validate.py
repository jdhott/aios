from pathlib import Path
api=Path('aios/api/app.py').read_text()
web=Path('aios/web_capture/app.py').read_text()
assert '[PROJECT TASK TRACE]' not in api
assert '[PROJECT TASK TRACE]' not in web
assert 'name="task_title"' in web
assert 'name="task_id"' in web
assert 'task_title: Annotated[list[str] | None, Form()]' in web
assert 'task_id: Annotated[list[str] | None, Form()]' in web
print('PASS: temporary project-task trace logging removed')
print('PASS: native project-task form submission preserved')
print('RESULT: PROJECT TASK TRACE CLEANUP V1 STRUCTURE VALID')
