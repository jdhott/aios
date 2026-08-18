from pathlib import Path
web=Path('aios/web_capture/app.py').read_text()
assert 'focus_parent_meta = ""' in web
assert '<div class="focus-parent-meta">Part of: ' in web
assert 'focus-title' in web and 'font-size:1.08rem' in web
assert 'focus-start-parent-meta' not in web
print('BNA breakdown child keeps parent context: PASS')
print('BNA title typography reduced: PASS')
print('Start Here remains uncluttered: PASS')
print('RESULT: BNA PARENT CONTEXT V1 SMOKE TEST PASSED')
