from pathlib import Path
import ast
text = Path('aios/web_capture/app.py').read_text()
checks = [
    ('snooze cancel exists', 'class="snooze-cancel"' in text),
    ('snooze cancel closes details', "removeAttribute('open')" in text or "removeAttribute(\\'open\\')" in text),
    ('pattern editor uses Save', '>Save</button>' in text),
    ('pattern editor has Done', '>Done</a>' in text),
    ('pattern update stays on editor', 'RedirectResponse(f"/work-patterns/{pattern_id}?saved=1",303)' in text),
    ('saved confirmation supported', 'saved == "1"' in text and '>Saved</div>' in text),
]
failed = False
for label, ok in checks:
    print(('PASS' if ok else 'FAIL') + ': ' + label)
    failed |= not ok
ast.parse(text)
print('web_capture app parses: PASS')
if failed:
    raise SystemExit('RESULT: WORK PATTERN SAVE + SNOOZE CANCEL V1 VALIDATION FAILED')
print('RESULT: WORK PATTERN SAVE + SNOOZE CANCEL V1 STRUCTURE VALID')
