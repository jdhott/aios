from pathlib import Path
web = Path('aios/web_capture/app.py').read_text()
checks = [
    ('serialized titles uses escaped JS newline', "titles.join('\\\\n')" in web),
    ('trash handler remains wired', "trash.onclick=function()" in web),
    ('dragstart handler remains wired', "addEventListener('dragstart'" in web),
    ('dragover reorder handler remains wired', "addEventListener('dragover'" in web),
    ('add row remains wired', 'onclick="addBreakdownRow(this)"' in web),
]
for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")
    assert ok, label
print('RESULT: BREAKDOWN LIST EDITOR RUNTIME FIX V1 STRUCTURE VALID')
