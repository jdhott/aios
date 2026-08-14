#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
capture = (root / "aios/ingestion/capture_metadata.py").read_text()
run = (root / "run_aios.py").read_text()

ast.parse(capture)
ast.parse(run)

checks = [
    (
        "prefix regex uses real whitespace matcher",
        'r"^(remember to|need to|i need to|todo:|to do:)\\s+"' in capture
        and 'r"^(remember to|need to|i need to|todo:|to do:)\\\\s+"' not in capture,
    ),
    (
        "protected globals declared",
        "CAPTURE_METADATA_PROTECTED_GLOBALS" in capture
        and '"clean_task_title"' in capture,
    ),
    (
        "configure helper skips protected globals",
        "if key in CAPTURE_METADATA_PROTECTED_GLOBALS:" in capture,
    ),
    (
        "canonical cleaner still exists",
        "def clean_task_title(text):" in capture,
    ),
    (
        "runtime uses canonical cleaner",
        "clean_task_title = capture_metadata_parser.clean_task_title" in run,
    ),
    (
        "v2 marker exists",
        'CAPTURE_PARSER_INDEPENDENCE_V2_VERSION = "app-service-boundary-v1-phase1.1-v2"' in run,
    ),
]

for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: CAPTURE PARSER INDEPENDENCE V2 VALIDATION FAILED")

print("RESULT: CAPTURE PARSER INDEPENDENCE V2 STRUCTURE VALID")
