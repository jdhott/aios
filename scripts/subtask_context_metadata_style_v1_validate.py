from pathlib import Path
web=Path('aios/web_capture/app.py').read_text()
assert '.task-parent-meta { margin-top:5px; color:var(--muted); font-size:.8rem; line-height:1.35; }' in web
assert '.task-parent-meta a { color:inherit; text-decoration:underline; font-weight:inherit; }' in web
assert '.task-parent-meta {{ margin-top:5px; color:var(--muted); font-size:.82rem; }}' in web
assert '.task-parent-meta a {{ color:inherit; text-decoration:underline; font-weight:inherit; }}' in web
assert 'color:var(--navy); text-decoration:none; font-weight:650' not in web
print('PASS: parent metadata matches surrounding task metadata')
print('PASS: parent link inherits metadata typography')
print('RESULT: SUBTASK CONTEXT METADATA STYLE V1 STRUCTURE VALID')
