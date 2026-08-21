from pathlib import Path

s = Path("aios/web_capture/app.py").read_text()
checks = [
    ("bottom navigation helper", "def _bottom_nav_html("),
    ("Home available", 'item("/", "Home", "⌂", "home")'),
    ("Projects available", 'item("/projects", "Projects", "▦", "projects")'),
    ("Reviews available", 'item("/reviews", "Reviews", "◎", "reviews", reviews_badge)'),
    ("New Task available", 'href="/tasks/new"'),
    ("Work Patterns available", 'href="/work-patterns">Work Patterns</a>'),
    ("Journal available", 'href="/journal">Journal</a>'),
    ("Sign Out available", 'class="bottom-nav-sheet-item sign-out-button"'),
    ("Home page heading", "home-page-heading"),
    ("Home bottom nav active", '_bottom_nav_html(active="home", review_count=review_count)'),
]
for label, needle in checks:
    assert needle in s, f"FAIL: {label}"
    print(f"PASS: {label}")
print("RESULT: DASHBOARD HEADER/NAV V1 STRUCTURE VALID")
