from pathlib import Path
s=Path("aios/web_capture/app.py").read_text()
assert "const menu = document.getElementById('dashboard-nav-menu');" not in s
assert s.count('const navMenu = document.getElementById("dashboard-nav-menu");') == 1
assert '!navMenu.contains(event.target)' in s
assert 'event.key === "Escape"' in s
print("PASS: malformed handler removed")
print("PASS: one clean dismissal handler")
print("RESULT: DASHBOARD MENU REPAIR VALID")
