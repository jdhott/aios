from pathlib import Path
text = Path('aios/web_capture/app.py').read_text()
assert '@app.post("/work-patterns/{pattern_id}")' in text
assert '?saved=1' in text
assert 'Save</button>' in text
assert 'Done</a>' in text
assert 'snooze-cancel' in text
assert 'Later today' in text and 'Tomorrow' in text and '1 week' in text
print('Pattern save-in-place flow present: PASS')
print('Pattern Done navigation present: PASS')
print('Snooze presets retained with Cancel: PASS')
print('RESULT: WORK PATTERN SAVE + SNOOZE CANCEL V1 SMOKE TEST PASSED')
