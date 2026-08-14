#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
capture = (root / "aios/ingestion/capture_metadata.py").read_text()
run = (root / "run_aios.py").read_text()
app_capture = (root / "scripts/app_inbox_capture.py").read_text()

for text in (capture, run, app_capture):
    ast.parse(text)

checks = [
    ("canonical cleaner exists", 'CAPTURE_TITLE_CLEANER_VERSION = "capture-title-cleaner-v1"' in capture and "def clean_task_title(text):" in capture),
    ("cleaner uses module sanitizer", "title = sanitize_task_title_separators(title)" in capture),
    ("parse_task_flags uses cleaner", "clean_title = clean_task_title(clean_title)" in capture),
    ("capture module has no run_aios import", "import run_aios" not in capture),
    ("runtime rebinds canonical cleaner", "clean_task_title = capture_metadata_parser.clean_task_title" in run),
    ("phase marker exists", 'CAPTURE_PARSER_INDEPENDENCE_VERSION = "app-service-boundary-v1-phase1.1"' in run),
    ("app capture directly imports parser", "from aios.ingestion.capture_metadata import parse_capture_metadata" in app_capture),
]

for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: CAPTURE PARSER INDEPENDENCE VALIDATION FAILED")

print("RESULT: CAPTURE PARSER INDEPENDENCE STRUCTURE VALID")
