#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
web = (root / "aios/web_capture/app.py").read_text()
deploy = (root / "scripts/deploy_cloud_run_web.sh").read_text()
ast.parse(web)

checks = [
    ("web marker", 'WEB_ABOUT_PAGE_VERSION = "about-page-v1"' in web),
    ("about payload helper", "def _web_about_payload(" in web),
    ("about page template", "def _about_page(" in web),
    ("about route", '@app.get("/about"' in web),
    ("about api", '@app.get("/api/about"' in web),
    ("more menu link", 'href="/about">About</a>' in web),
    ("build git sha env", "AIOS_WEB_GIT_SHA" in web),
    ("deploy sets git sha", "AIOS_WEB_GIT_SHA=${GIT_SHA}" in deploy),
    ("deploy sets build time", "AIOS_WEB_BUILD_TIME=${BUILD_TIME}" in deploy),
    ("health exposes about marker", '"about_page": payload["about_page"]' in web),
]

for label, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + label)
if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: ABOUT PAGE V1 VALIDATION FAILED")
print("RESULT: ABOUT PAGE V1 STRUCTURE VALID")
