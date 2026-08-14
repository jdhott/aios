#!/usr/bin/env python3
"""Static/runtime-order smoke for top-level possible-duplicate shadow execution."""
from __future__ import annotations

import ast
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "run_aios.py").read_text()
    tree = ast.parse(text)

    definition = None
    calls = []

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.FunctionDef)
            and node.name
            == "shadow_possible_duplicate_review"
        ):
            definition = node

        elif isinstance(node, ast.Call):
            fn = node.func
            if (
                isinstance(fn, ast.Name)
                and fn.id
                == "shadow_possible_duplicate_review"
            ):
                calls.append(node)

    if definition is None:
        raise RuntimeError(
            "shadow_possible_duplicate_review definition missing"
        )

    if not calls:
        raise RuntimeError(
            "shadow_possible_duplicate_review call missing"
        )

    first_call = min(
        call.lineno for call in calls
    )

    if definition.lineno >= first_call:
        raise RuntimeError(
            "Shadow helper would be called before it is defined."
        )

    # Ensure the live classification call still follows the authoritative
    # Notion UI call in source order.
    notion_pos = text.find(
        "inbox_review_ui.show_possible_duplicate("
    )
    shadow_pos = text.find(
        "            shadow_possible_duplicate_review(match)"
    )

    if (
        notion_pos < 0
        or shadow_pos < 0
        or notion_pos >= shadow_pos
    ):
        raise RuntimeError(
            "Notion review render no longer precedes shadow write."
        )

    print(
        "Shadow helper definition before runtime call: PASS"
    )
    print(
        "Notion UI remains first in review path: PASS"
    )
    print(
        "Existing shadow helper preserved: PASS"
    )
    print(
        "RESULT: POSSIBLE DUPLICATE SHADOW EXECUTION ORDER "
        "SMOKE TEST PASSED"
    )


if __name__ == "__main__":
    main()
