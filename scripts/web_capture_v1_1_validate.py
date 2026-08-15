#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
app = (root / "aios/web_capture/app.py").read_text()

ast.parse(app)

checks = [
    (
        "v1.1 marker exists",
        'WEB_CAPTURE_MULTILINE_VERSION = "aios-web-capture-v1.1"' in app,
    ),
    (
        "brain dump splitter exists",
        "def _split_brain_dump(" in app,
    ),
    (
        "split uses line breaks",
        ".splitlines()" in app,
    ),
    (
        "blank lines ignored",
        "if line.strip()" in app,
    ),
    (
        "batch capture helper exists",
        "def _capture_many(" in app,
    ),
    (
        "each line uses canonical API capture",
        "_capture_to_aios(line)" in app,
    ),
    (
        "partial failure handling exists",
        "if failures:" in app,
    ),
    (
        "single item grammar supported",
        'label = "item" if sent == 1 else "items"' in app,
    ),
    (
        "UI explains one line per task",
        "One line per task." in app,
    ),
]

for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: AIOS WEB CAPTURE V1.1 VALIDATION FAILED")

print("RESULT: AIOS WEB CAPTURE V1.1 STRUCTURE VALID")
