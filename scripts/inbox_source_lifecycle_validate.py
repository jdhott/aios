#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path


def function_source(text, function_name):
    tree = ast.parse(text)
    lines = text.splitlines()

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return "\n".join(
                lines[node.lineno - 1:node.end_lineno]
            )

    raise RuntimeError(f"Function not found: {function_name}")


def main():
    root = Path(__file__).resolve().parents[1]

    run_text = (root / "run_aios.py").read_text()
    source_text = (
        root / "aios" / "ingestion" / "source.py"
    ).read_text()
    notion_text = (
        root / "aios" / "ingestion" / "notion_source.py"
    ).read_text()

    created = function_source(
        run_text,
        "archive_created_item",
    )
    reviewed = function_source(
        run_text,
        "archive_reviewed_items",
    )

    checks = [
        (
            "InboxSource defines remove_item",
            "def remove_item(self, item: InboxItem)" in source_text,
        ),
        (
            "NotionInboxSource defines remove_item",
            "def remove_item(self, item: InboxItem)" in notion_text,
        ),
        (
            "Notion source removes by source-neutral id",
            "delete_original_block(item.source_item_id)"
            in notion_text,
        ),
        (
            "created-item pipeline uses source lifecycle",
            "inbox_source.remove_item(item)"
            in created,
        ),
        (
            "reviewed-item pipeline uses source lifecycle",
            "inbox_source.remove_item(item)"
            in reviewed,
        ),
        (
            "created-item pipeline no longer knows block_id",
            'item["block_id"]' not in created,
        ),
        (
            "reviewed-item pipeline no longer knows block_id",
            'item["block_id"]' not in reviewed,
        ),
        (
            "duplicate-review Notion UI remains untouched",
            run_text.count('item["block_id"]') == 2,
        ),
        (
            "pipeline still reads through inbox source",
            "inbox_source.list_pending_items()" in run_text,
        ),
    ]

    ast.parse(run_text)
    ast.parse(source_text)
    ast.parse(notion_text)

    for label, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}: {label}")

    if not all(ok for _, ok in checks):
        print(
            "\nRESULT: INBOX SOURCE LIFECYCLE CUTOVER "
            "VALIDATION FAILED"
        )
        raise SystemExit(1)

    print(
        "\nRESULT: INBOX SOURCE LIFECYCLE CUTOVER "
        "STRUCTURE VALID"
    )


if __name__ == "__main__":
    main()
