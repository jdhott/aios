from pathlib import Path
text = Path("aios/web_capture/app.py").read_text()
assert "width:260px" in text
assert "minmax(145px,1fr) auto" in text
assert "min-width:145px" in text
assert 'snooze-cancel' in text
print("Date field has usable width: PASS")
print("Cancel remains available: PASS")
print("RESULT: SNOOZE MENU WIDTH FIX V1 SMOKE TEST PASSED")
