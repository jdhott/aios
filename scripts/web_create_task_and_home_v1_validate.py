#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
api = (root / "aios/api/app.py").read_text()
web = (root / "aios/web_capture/app.py").read_text()
ast.parse(api)
ast.parse(web)

checks = [
    ("create task API marker", 'AIOS_WEB_CREATE_TASK_VERSION = "create-task-v1"' in api),
    ("POST /tasks endpoint", '@app.post("/tasks"' in api),
    ("new task web marker", 'WEB_CREATE_TASK_VERSION = "create-task-v1"' in web),
    ("New Task dashboard navigation", 'href="/tasks/new"' in web),
    ("Home navigation on projects", '>Home</a>' in web),
    ("new task page renderer", "def _create_task_page(" in web),
    ("new task GET route", '@app.get("/tasks/new")' in web),
    ("new task POST route", '@app.post("/tasks/new")' in web),
    ("project selection present", 'name="project_id"' in web),
    ("authenticated task create", 'requests.post(' in web and 'Authorization' in web),
    ("create returns to dashboard", 'url="/?message=Task+created."' in web),
]

for label, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + label)

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: CREATE TASK + HOME V1 VALIDATION FAILED")

print("RESULT: CREATE TASK + HOME V1 STRUCTURE VALID")
