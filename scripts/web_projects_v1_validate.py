#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
api = (root / "aios/api/app.py").read_text()
web = (root / "aios/web_capture/app.py").read_text()
ast.parse(api)
ast.parse(web)

checks = [
    ("API projects marker", 'AIOS_PROJECTS_WEB_VERSION = "projects-v1"' in api),
    ("projects endpoints", '@app.get("/projects"' in api and '@app.get("/projects/{project_id}"' in api),
    ("web projects marker", 'WEB_PROJECTS_VERSION = "projects-v1"' in web),
    ("dashboard Projects link", 'href="/projects"' in web),
    ("projects page renderer", "def _projects_page(" in web),
    ("project detail renderer", "def _project_detail_page(" in web),
    ("authenticated project fetch", 'headers={"Authorization": f"Bearer {token}"}' in web),
]

for label, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + label)

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: AIOS PROJECTS V1 FIX1 VALIDATION FAILED")

print("RESULT: AIOS PROJECTS V1 FIX1 STRUCTURE VALID")
