#!/usr/bin/env python3
import ast
from pathlib import Path

MOVED = {
    "parse_manual_project_tag",
    "parse_task_flags",
    "sanitize_task_title_separators",
    "strip_due_date_phrases",
    "extract_due_date",
}

def funcs(text):
    return {
        n.name
        for n in ast.walk(ast.parse(text))
        if isinstance(n, ast.FunctionDef)
    }

def main():
    root = Path(__file__).resolve().parents[1]
    run_text = (root / "run_aios.py").read_text()
    module_text = (root / "aios" / "ingestion" / "capture_metadata.py").read_text()

    checks = [
        ("parser implementations removed from run_aios", not (MOVED & funcs(run_text))),
        ("parser implementations live in module", MOVED <= funcs(module_text)),
        ("runtime configures parser module", "configure_capture_metadata(globals())" in run_text),
        ("legacy names rebound", all(f"capture_metadata_parser.{n}" in run_text for n in MOVED)),
        ("CaptureMetadata exists", "class CaptureMetadata" in module_text),
        ("parse_capture_metadata exists", "def parse_capture_metadata" in module_text),
        ("prepare_task_title remains in runtime", "def prepare_task_title(" in run_text),
    ]

    for label, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}: {label}")

    if not all(ok for _, ok in checks):
        print("\nRESULT: CAPTURE METADATA PARSER EXTRACTION VALIDATION FAILED")
        raise SystemExit(1)

    print("\nRESULT: CAPTURE METADATA PARSER EXTRACTION STRUCTURE VALID")

if __name__ == "__main__":
    main()
