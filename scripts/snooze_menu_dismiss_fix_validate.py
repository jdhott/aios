from pathlib import Path
s=Path("aios/web_capture/app.py").read_text()
assert "snooze-cancel" not in s
assert s.count("const snoozeMenus = Array.from(")==1
assert "!menu.contains(event.target)" in s
assert 'event.key !== "Escape"' in s
assert "if (other !== menu) other.open = false;" in s
print("PASS: Cancel removed")
print("PASS: outside click dismissal")
print("PASS: Escape dismissal")
print("PASS: only one snooze menu stays open")
print("RESULT: SNOOZE MENU DISMISS FIX VALID")
