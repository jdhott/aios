from pathlib import Path

s = Path("aios/web_capture/app.py").read_text()
checks = [
    ("bottom navigation helper", "def _bottom_nav_html("),
    ("Home available", 'item("/", "Home", "⌂", "home")'),
    ("Projects available", 'item("/projects", "Projects", "▦", "projects")'),
    ("Reviews available", 'item("/reviews", "Reviews", "◎", "reviews", reviews_badge)'),
    ("New Task available", 'href="/tasks/new"'),
    ("Work Patterns available", '<a href="/work-patterns">Work Patterns</a>'),
    ("Journal available", '<a href="/journal">Journal</a>'),
    ("Sign Out available", '<button type="submit">Sign Out</button>'),
    ("Dashboard page heading", 'class="page-heading"'),
    ("Dashboard bottom nav active", '_bottom_nav_html(active="home", review_count=review_count)'),
]
for label, needle in checks:
    assert needle in s, f"FAIL: {label}"
    print(f"PASS: {label}")
print("RESULT: DASHBOARD HEADER/NAV V1 STRUCTURE VALID")
