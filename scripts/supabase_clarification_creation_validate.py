"""
Read-only structural validation for Supabase-primary clarification creation.

Run:
    python -m scripts.supabase_clarification_creation_validate
"""

from __future__ import annotations

from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    runtime = (root / "run_aios.py").read_text()

    clarify_branch = runtime[
        runtime.index('elif decision == "clarify":'):
        runtime.index('    else:', runtime.index('elif decision == "clarify":'))
    ]

    dispatcher_start = runtime.index("def create_notion_task(")
    dispatcher_end = runtime.index(
        "def create_and_update_task(",
        dispatcher_start,
    )
    dispatcher = runtime[
        dispatcher_start:
        dispatcher_end
    ]

    checks = [
        (
            "clarification branch requests Supabase-primary creation",
            "supabase_primary=True"
            in clarify_branch,
        ),
        (
            "dispatcher no longer excludes clarification tasks",
            "and not is_clarification"
            not in dispatcher,
        ),
        (
            "top-level Supabase-primary guard remains",
            'AIOS_DATASTORE == "supabase"'
            in dispatcher
            and "parent_task_id is None"
            in dispatcher
            and "step_order is None"
            in dispatcher,
        ),
        (
            "Notion mirror creator still supplied",
            "notion_create_fn=_create_notion_task_only"
            in dispatcher,
        ),
        (
            "Notion rollback still supplied",
            "notion_rollback_fn=update_notion_page"
            in dispatcher,
        ),
        (
            "clarification UI remains attached after creation",
            "maybe_add_clarification_blocks("
            in runtime,
        ),
        (
            "clarification resolution remains datastore-aware",
            "updated_task = update_task_lifecycle("
            in runtime
            and "updated_task = update_task_metadata("
            in runtime,
        ),
    ]

    failed = [
        label
        for label, ok in checks
        if not ok
    ]

    for label, ok in checks:
        print(
            f"{'PASS' if ok else 'FAIL'}: "
            f"{label}"
        )

    if failed:
        print(
            "\nRESULT: CLARIFICATION CREATION "
            "CUTOVER VALIDATION FAILED"
        )
        for label in failed:
            print(f"  - {label}")
        raise SystemExit(1)

    print(
        "\nRESULT: CLARIFICATION CREATION "
        "CUTOVER STRUCTURE VALID"
    )


if __name__ == "__main__":
    main()
