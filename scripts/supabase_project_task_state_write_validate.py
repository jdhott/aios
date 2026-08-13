"""
Read-only validation for the Supabase Project task-state write cutover.

Checks that:
- Suggested Project is supported by the canonical task metadata writer.
- the task/project relation writer exposes Supabase-only relation writes.
- run_aios binds all three project task-state mutation seams.

Run:
    python -m scripts.supabase_project_task_state_write_validate
"""

from __future__ import annotations

from pathlib import Path

from aios.storage import task_metadata_writer
from aios.storage.task_project_relation_writer import (
    SupabaseProjectRelationWriter,
)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    runtime = (root / "run_aios.py").read_text()

    checks = [
        (
            "Suggested Project metadata support",
            "Suggested Project"
            in task_metadata_writer.SUPPORTED_PROPERTIES,
        ),
        (
            "Supabase relation writer available",
            hasattr(
                SupabaseProjectRelationWriter,
                "write_supabase",
            ),
        ),
        (
            "Suggested Project staging bridge bound",
            "project_helpers.update_suggested_project_if_needed = ("
            in runtime,
        ),
        (
            "Suggested Project canonical bridge bound",
            "project_helpers.set_suggested_project_canonical = ("
            in runtime,
        ),
        (
            "Review relation bridge bound",
            "project_helpers.set_review_project_relation_if_empty = ("
            in runtime,
        ),
        (
            "Supabase-only review relation marker present",
            "Supabase-only REVIEW project relation"
            in runtime,
        ),
        (
            "Supabase-only Suggested Project marker present",
            "Supabase-only staging write"
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
            "\nRESULT: PROJECT TASK-STATE "
            "WRITE CUTOVER VALIDATION FAILED"
        )
        for label in failed:
            print(
                f"  - {label}"
            )
        raise SystemExit(1)

    print(
        "\nRESULT: PROJECT TASK-STATE "
        "WRITE CUTOVER STRUCTURE VALID"
    )


if __name__ == "__main__":
    main()
