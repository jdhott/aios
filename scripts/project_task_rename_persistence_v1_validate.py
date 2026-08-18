from pathlib import Path
web = Path('aios/web_capture/app.py').read_text()
api = Path('aios/api/app.py').read_text()
checks = [
    ('inline title changes are remembered as they are typed', "title.addEventListener('input',remember)" in web),
    ('title change events are remembered', "title.addEventListener('change',remember)" in web),
    ('save serializes the live input value', 'const liveTitle=input?input.value' in web),
    ('save caches the live value before submit', 'row.dataset.editedTitle=liveTitle' in web),
    ('bulk project update persists title and order together', '.update({"title": title, "project_order": order' in api),
]
failed=[]
for label, ok in checks:
    print(('PASS: ' if ok else 'FAIL: ') + label)
    if not ok: failed.append(label)
if failed:
    raise SystemExit('RESULT: PROJECT TASK RENAME PERSISTENCE V1 VALIDATION FAILED')
print('RESULT: PROJECT TASK RENAME PERSISTENCE V1 STRUCTURE VALID')
