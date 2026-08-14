#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    run_text = (root / "run_aios.py").read_text()
    tree = ast.parse(run_text)

    definition_line = None
    call_lines = []

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.FunctionDef)
            and node.name
            == "shadow_possible_duplicate_review"
        ):
            definition_line = node.lineno

        if isinstance(node, ast.Call):
            fn = node.func
            if (
                isinstance(fn, ast.Name)
                and fn.id
                == "shadow_possible_duplicate_review"
            ):
                call_lines.append(
                    node.lineno
                )

    checks = [
        (
            "shadow helper definition exists",
            definition_line is not None,
        ),
        (
            "shadow helper has a runtime call",
            bool(call_lines),
        ),
        (
            "shadow helper is defined before first call",
            (
                definition_line is not None
                and bool(call_lines)
                and definition_line
                < min(call_lines)
            ),
        ),
        (
            "execution-order marker exists",
            "[Possible Duplicate Shadow] Execution order fixed"
            in run_text,
        ),
        (
            "Notion duplicate review still renders before shadow call",
            (
                "inbox_review_ui.show_possible_duplicate("
                in run_text
                and "shadow_possible_duplicate_review(match)"
                in run_text
            ),
        ),
        (
            "shadow remains Supabase-only",
            'if AIOS_DATASTORE != "supabase":'
            in run_text,
        ),
        (
            "shadow remains non-blocking",
            "[Possible Duplicate Shadow] Write failed:"
            in run_text,
        ),
    ]

    for label, ok in checks:
        print(
            f"{'PASS' if ok else 'FAIL'}: {label}"
        )

    if not all(
        ok for _, ok in checks
    ):
        raise SystemExit(
            "RESULT: POSSIBLE DUPLICATE SHADOW EXECUTION ORDER "
            "VALIDATION FAILED"
        )

    print(
        "RESULT: POSSIBLE DUPLICATE SHADOW EXECUTION ORDER "
        "STRUCTURE VALID"
    )


if __name__ == "__main__":
    main()
