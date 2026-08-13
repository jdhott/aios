#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path

CANONICAL = {
    "create_archive_section",
    "archive_item",
    "append_archive_toggle",
    "find_child_toggle_by_title",
    "get_or_create_archive_toggle",
    "archive_non_task_item",
    "archive_non_task_note_item",
    "archive_non_task_idea_item",
    "delete_original_block",
    "trim_archive_runs",
}

ORCHESTRATION = {"archive_created_item", "archive_reviewed_items"}

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
    archive_path = root / "aios" / "notion" / "archive.py"
    if not archive_path.exists():
        print("FAIL: aios/notion/archive.py exists")
        raise SystemExit(1)

    module_text = archive_path.read_text()
    run_funcs = functions(run_text)
    module_funcs = functions(module_text)

    checks = [
        ("ten archive helpers removed from run_aios", not (CANONICAL & run_funcs)),
        ("ten archive helpers exist in canonical module", CANONICAL <= module_funcs),
        ("runtime configures archive module", "archive_helpers.configure_archive_module(globals())" in run_text),
        ("runtime binds canonical archive helpers", all(f"archive_helpers.{name}" in run_text for name in CANONICAL)),
        ("archive pipeline orchestration remains in runtime", ORCHESTRATION <= run_funcs),
        ("module remains Notion block interface code", "/v1/blocks/" in module_text and "/v1/pages/" not in module_text),
        ("Supabase persistence APIs are not introduced", "supabase" not in module_text.lower()),
    ]

    for label, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}: {label}")

    if not all(ok for _, ok in checks):
        print("\nRESULT: BRAIN DUMP ARCHIVE MODULE CONSOLIDATION VALIDATION FAILED")
        raise SystemExit(1)

    print("\nRESULT: BRAIN DUMP ARCHIVE MODULE CONSOLIDATION STRUCTURE VALID")

if __name__ == "__main__":
    main()
