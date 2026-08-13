#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path


CANONICAL = {
    "append_clarification_blocks",
    "get_checked_clarification_action",
    "update_task_from_selection",
    "clear_page_children",
    "update_clarification_title",
    "process_clarification_selection",
}


def functions(text: str) -> dict[str, ast.FunctionDef]:
    tree = ast.parse(text)
    return {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }


def source_for(text: str, node: ast.FunctionDef) -> str:
    lines = text.splitlines()
    return "\n".join(
        lines[node.lineno - 1:node.end_lineno]
    )


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    run_text = (root / "run_aios.py").read_text()
    module_text = (
        root / "aios" / "clarification.py"
    ).read_text()

    run_funcs = functions(run_text)
    module_funcs = functions(module_text)

    update_selection = source_for(
        module_text,
        module_funcs["update_task_from_selection"],
    )
    update_title = source_for(
        module_text,
        module_funcs["update_clarification_title"],
    )
    process = source_for(
        module_text,
        module_funcs["process_clarification_selection"],
    )

    checks = [
        (
            "six workflow functions removed from run_aios",
            not (CANONICAL & set(run_funcs)),
        ),
        (
            "six workflow functions exist in module",
            CANONICAL <= set(module_funcs),
        ),
        (
            "runtime configures clarification module",
            "clarification_helpers.configure_clarification_module(globals())"
            in run_text,
        ),
        (
            "runtime binds canonical module functions",
            all(
                f"clarification_helpers.{name}"
                in run_text
                for name in CANONICAL
            ),
        ),
        (
            "selection update is datastore-aware",
            "update_task_lifecycle(" in update_selection
            and "update_task_metadata(" in update_selection
            and "datastore=AIOS_DATASTORE" in update_selection
            and "requests.patch(" not in update_selection,
        ),
        (
            "clarification title update is datastore-aware",
            "update_task_lifecycle(" in update_title
            and "datastore=AIOS_DATASTORE" in update_title
            and "requests.patch(" not in update_title,
        ),
        (
            "accepted clarification loop guard preserved",
            "prepare_accepted_clarification_title(text)"
            in process
            and "Human acceptance is authoritative"
            in process,
        ),
        (
            "pipeline orchestration remains in runtime",
            "def maybe_add_clarification_blocks("
            in run_text,
        ),
    ]

    for label, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}: {label}")

    if not all(ok for _, ok in checks):
        print(
            "\nRESULT: CLARIFICATION MODULE CONSOLIDATION "
            "VALIDATION FAILED"
        )
        raise SystemExit(1)

    print(
        "\nRESULT: CLARIFICATION MODULE CONSOLIDATION "
        "STRUCTURE VALID"
    )


if __name__ == "__main__":
    main()
