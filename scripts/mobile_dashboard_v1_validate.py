from pathlib import Path

s = Path("aios/web_capture/app.py").read_text()

checks = [
    ("shared mobile shell", "def _mobile_shell_css() -> str:" in s),
    ("bottom navigation helper", "def _bottom_nav_html(" in s),
    ("Home in bottom nav", 'item("/", "Home", "⌂", "home")' in s),
    ("Projects in bottom nav", 'item("/projects", "Projects", "▦", "projects")' in s),
    ("New task action", 'href="/tasks/new"' in s),
    ("Reviews in bottom nav", 'item("/reviews", "Reviews", "◎", "reviews", reviews_badge)' in s),
    ("More retains Work Patterns", '<a href="/work-patterns">Work Patterns</a>' in s),
    ("More retains Journal", '<a href="/journal">Journal</a>' in s),
    ("dashboard renders bottom nav", '_bottom_nav_html(active="home", review_count=review_count)' in s),
    ("mobile breakpoint retained", "@media (max-width:560px)" in s),
    ("Start Here heading retained", '<div class="focus-start-heading">Start here</div>' in s),
    ("Start Here actions retained", 'class="focus-step-actions"' in s),
    ("timebox integrated into Start Here", 'focus-timebox-inline' in s),
]

for label, ok in checks:
    assert ok, f"FAIL: {label}"
    print(f"PASS: {label}")
print("RESULT: MOBILE DASHBOARD V1 STRUCTURE VALID")
