from pathlib import Path
web=Path('aios/web_capture/app.py').read_text()
assert 'Part of: ' in web
assert 'task-parent-meta' in web
assert 'color:inherit; text-decoration:underline; font-weight:inherit' in web
print('Subtask parent remains linked: PASS')
print('Parent context uses muted metadata styling: PASS')
print('RESULT: SUBTASK CONTEXT METADATA STYLE V1 SMOKE TEST PASSED')
