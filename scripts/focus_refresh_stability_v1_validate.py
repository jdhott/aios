#!/usr/bin/env python3
from pathlib import Path

source = Path('aios/web_capture/app.py').read_text()

checks = [
    ('refresh pending state', 'refresh_pending = bool(' in source),
    ('pending waits for activation', 'or not activation_id' in source),
    ('provisional focus suppressed', 'if focus and not refresh_pending:' in source),
    ('single updating state', '<div class="focus-pending">Updating your focus…</div>' in source),
    ('refresh loop follows pending state', 'refresh_needed = refresh_pending' in source),
]

failed = False
for name, ok in checks:
    print(('PASS' if ok else 'FAIL') + ': ' + name)
    failed = failed or not ok

if failed:
    raise SystemExit(1)
print('RESULT: FOCUS REFRESH STABILITY V1 STRUCTURE VALID')
