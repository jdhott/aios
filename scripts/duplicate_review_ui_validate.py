#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path


MOVED = {
    "has_possible_duplicate_blocks",
    "append_possible_duplicate_blocks",
    "get_checked_possible_duplicate_action",
}


def functions(text):
    tree = ast.parse(text)
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }


def main():
    root = Path(__file__).resolve().parents[1]

    run_text = (root / "run_aios.py").read_text()
    notion_text = (
        root
        / "aios"
        / "notion"
        / "duplicate_review.py"
    ).read_text()
    interface_text = (
        root
        / "aios"
        / "review"
        / "interface.py"
    ).read_text()

    run_funcs = functions(run_text)
    notion_funcs = functions(notion_text)

    checks = [
        (
            "InboxReviewUI protocol exists",
            "class InboxReviewUI(Protocol)"
            in interface_text,
        ),
        (
            "NotionInboxReviewUI exists",
            "class NotionInboxReviewUI"
            in notion_text,
        ),
        (
            "duplicate-review helpers left run_aios",
            not (MOVED & run_funcs),
        ),
        (
            "duplicate-review helpers live in Notion module",
            MOVED <= notion_funcs,
        ),
        (
            "runtime configures review UI",
            "configure_duplicate_review_ui(globals())"
            in run_text,
        ),
        (
            "pipeline renders through review boundary",
            "inbox_review_ui.show_possible_duplicate("
            in run_text,
        ),
        (
            "legacy Notion action read remains available",
            ".get_possible_duplicate_action(item)" in run_text
            and 'AIOS_DATASTORE == "notion"' in run_text,
        ),
        (
            "core runtime no longer accesses item block_id",
            'item["block_id"]' not in run_text,
        ),
        (
            "Notion review UI uses source-neutral item id",
            "item.source_item_id" in notion_text,
        ),
        (
            "Notion review UI remains block-only presentation",
            "/v1/blocks/" in notion_text
            and "/v1/pages/" not in notion_text,
        ),
    ]

    ast.parse(run_text)
    ast.parse(notion_text)
    ast.parse(interface_text)

    for label, ok in checks:
        print(
            f"{'PASS' if ok else 'FAIL'}: {label}"
        )

    if not all(ok for _, ok in checks):
        print(
            "\nRESULT: DUPLICATE REVIEW UI CUTOVER "
            "VALIDATION FAILED"
        )
        raise SystemExit(1)

    print(
        "\nRESULT: DUPLICATE REVIEW UI CUTOVER "
        "STRUCTURE VALID"
    )


if __name__ == "__main__":
    main()
