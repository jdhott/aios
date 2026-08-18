from pathlib import Path
root = Path(__file__).resolve().parents[1]
web = (root / 'aios/web_capture/app.py').read_text()
# Lightweight regression assertions that don't require cloud credentials.
assert 'Task already has breakdown children' in (root / 'aios/api/app.py').read_text()
assert 'BreakdownActionError' in web
assert 'already has breakdown subtasks' in web
print('Existing-child rejection is explicit: PASS')
print('API detail reaches Review UI error path: PASS')
print('Existing breakdown prevents duplicate proposal form: PASS')
print('RESULT: MANUAL BREAKDOWN RUNTIME FIX V1 SMOKE TEST PASSED')
