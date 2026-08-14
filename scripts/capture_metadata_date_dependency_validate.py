#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path


def top_level_names(text):
    names = set()
    for node in ast.parse(text).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.FunctionDef):
            names.add(node.name)
    return names


def main():
    root = Path(__file__).resolve().parents[1]

    run_text = (root / "run_aios.py").read_text()
    module_text = (
        root
        / "aios"
        / "ingestion"
        / "capture_metadata.py"
    ).read_text()

    run_names = top_level_names(run_text)
    module_names = top_level_names(module_text)

    required = {
        "MONTH_NAME_PATTERN",
        "MONTH_DAY_DATE_PATTERN",
        "DUE_DATE_WORD_PATTERNS",
        "_next_weekday_date",
    }

    checks = [
        (
            "date parser dependencies live in canonical module",
            required <= module_names,
        ),
        (
            "runtime no longer owns date parser definitions",
            not (
                required
                & {
                    name
                    for name in run_names
                    if not name.startswith("capture_metadata_parser")
                }
            ),
        ),
        (
            "runtime compatibility aliases remain",
            "MONTH_NAME_PATTERN = capture_metadata_parser.MONTH_NAME_PATTERN"
            in run_text
            and "DUE_DATE_WORD_PATTERNS = capture_metadata_parser.DUE_DATE_WORD_PATTERNS"
            in run_text
            and "_next_weekday_date = capture_metadata_parser._next_weekday_date"
            in run_text,
        ),
        (
            "parser imports regex/date primitives itself",
            "import re" in module_text
            and "from datetime import datetime, timedelta"
            in module_text,
        ),
        (
            "extract_due_date consumes local month pattern",
            "MONTH_NAME_PATTERN" in module_text,
        ),
        (
            "strip_due_date_phrases consumes local due patterns",
            "for pattern in DUE_DATE_WORD_PATTERNS"
            in module_text,
        ),
    ]

    ast.parse(run_text)
    ast.parse(module_text)

    for label, ok in checks:
        print(
            f"{'PASS' if ok else 'FAIL'}: {label}"
        )

    if not all(ok for _, ok in checks):
        print(
            "\nRESULT: CAPTURE METADATA DATE DEPENDENCY FIX "
            "VALIDATION FAILED"
        )
        raise SystemExit(1)

    print(
        "\nRESULT: CAPTURE METADATA DATE DEPENDENCY FIX "
        "STRUCTURE VALID"
    )


if __name__ == "__main__":
    main()
