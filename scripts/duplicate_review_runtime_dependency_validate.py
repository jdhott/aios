#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path


def function_end_line(text: str, name: str) -> int:
    tree = ast.parse(text)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node.end_lineno
    raise RuntimeError(f"Missing function: {name}")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    run_text = (root / "run_aios.py").read_text()
    dup_text = (
        root
        / "aios"
        / "notion"
        / "duplicate_review.py"
    ).read_text()

    marker = "[Inbox Review UI] Runtime dependencies refreshed"
    score_end = function_end_line(run_text, "score_label")
    run_lines = run_text.splitlines()

    refresh_line = next(
        (
            i + 1
            for i, line in enumerate(run_lines)
            if "duplicate_review_ui.configure_duplicate_review_ui(globals())" in line
            and i + 1 > score_end
        ),
        None,
    )

    checks = [
        (
            "runtime refresh occurs after score_label",
            refresh_line is not None,
        ),
        (
            "runtime refresh marker exists",
            marker in run_text,
        ),
        (
            "legacy block_id access removed",
            'item["block_id"]' not in dup_text
            and "item['block_id']" not in dup_text,
        ),
        (
            "source-neutral source_item_id used for PATCH",
            "item.source_item_id" in dup_text
            and "/children" in dup_text,
        ),
        (
            "Notion review UI remains configured",
            "NotionInboxReviewUI" in dup_text
            and "inbox_review_ui = duplicate_review_ui.NotionInboxReviewUI()"
            in run_text,
        ),
        (
            "possible-duplicate shadow integration remains present",
            "def shadow_possible_duplicate_review(" in run_text,
        ),
    ]

    ast.parse(run_text)
    ast.parse(dup_text)

    for label, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}: {label}")

    if not all(ok for _, ok in checks):
        raise SystemExit(
            "RESULT: DUPLICATE REVIEW RUNTIME DEPENDENCY FIX VALIDATION FAILED"
        )

    print(
        "RESULT: DUPLICATE REVIEW RUNTIME DEPENDENCY FIX STRUCTURE VALID"
    )


if __name__ == "__main__":
    main()
