from pathlib import Path
s=Path("aios/web_capture/app.py").read_text()
checks=[
("AIOS home link",'class="app-home" href="/">AIOS</a>'),
("Projects primary",'<a href="/projects">Projects</a>'),
("Reviews primary",'href="/reviews">{f"Reviews ({review_count})"'),
("New Task primary",'class="new-task-link" href="/tasks/new">+ New Task</a>'),
("menu exists",'class="nav-menu"'),
("Work Patterns available",'<a href="/work-patterns">Work Patterns</a>'),
("Journal available",'<a href="/journal">Journal</a>'),
("Sign Out available",'<button type="submit">Sign Out</button>'),
("Dashboard page heading",'class="page-heading"'),
("mobile reduction",'.dashboard-nav > a:not(.new-task-link) {{ display:none; }}'),
]
for label,needle in checks:
    assert needle in s, f"FAIL: {label}"
    print(f"PASS: {label}")
print("RESULT: DASHBOARD HEADER NAV V1 STRUCTURE VALID")
