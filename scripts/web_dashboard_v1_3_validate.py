#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
web = (root / "aios/web_capture/app.py").read_text()
ast.parse(web)

checks = [
    ("interaction marker", 'WEB_DASHBOARD_INTERACTION_VERSION = "aios-web-dashboard-v1.3-scroll-checkmark"' in web),
    ("scroll stored", 'sessionStorage.setItem(scrollKey, String(window.scrollY))' in web),
    ("scroll restored", "window.scrollTo" in web and "sessionStorage.removeItem(scrollKey)" in web),
    ("complete click intercepted", 'button.addEventListener("click"' in web),
    ("checkmark state", 'button.classList.add("is-completing")' in web),
    ("checkmark rendered", 'content:"✓"' in web),
    ("delete preserves scroll", 'document.querySelectorAll(".delete-form")' in web),
]
for label, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + label)

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: WEB DASHBOARD V1.3 VALIDATION FAILED")

print("RESULT: WEB DASHBOARD V1.3 STRUCTURE VALID")
