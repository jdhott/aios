#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
web = (root / "aios/web_capture/app.py").read_text()
ast.parse(web)

checks = [
    ("web marker", 'WEB_DARK_MODE_VERSION = "dark-mode-v1"' in web),
    ("dark tokens block", "_DARK_DESIGN_TOKENS" in web),
    ("system dark media query", '@media (prefers-color-scheme: dark)' in web),
    ("manual dark override", ':root[data-theme="dark"]' in web),
    ("manual light override", ':root[data-theme="light"]' in web),
    ("theme init script", 'localStorage.getItem("aios-theme")' in web),
    ("theme toggle control", "data-theme-toggle" in web),
    ("theme meta tags", 'media="(prefers-color-scheme: light)"' in web),
    ("nav uses token bg", "background: var(--nav-bg)" in web),
    ("capture uses shared tokens", "def _capture_pwa_page()" in web and "_mobile_design_tokens()" in web),
]

for label, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + label)
if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: DARK MODE V1 VALIDATION FAILED")
print("RESULT: DARK MODE V1 STRUCTURE VALID")
