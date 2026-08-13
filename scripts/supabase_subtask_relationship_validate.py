"""
Read-only validation of Supabase parent/subtask relationships.

Legacy migrated children are allowed to have no step_order because
the source Notion dataset contains historical parent relationships
without Step Order values.

New Supabase-primary hierarchy creation is separately proven by
supabase_subtask_creation_write_smoke.py, which requires step_order
for every newly-created child.

Run:
    python -m scripts.supabase_subtask_relationship_validate
"""

from __future__ import annotations

from collections import Counter

from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_repository import TaskRepository


LEGACY_MISSING_STEP_ORDER_BASELINE = 46


def main() -> None:
    print("=" * 72)
    print(
        "AIOS SUPABASE SUBTASK "
        "RELATIONSHIP VALIDATION"
    )
    print("=" * 72)

    print("\nREAD ONLY.")

    repo = TaskRepository(
        SupabaseStore()
    )

    tasks = repo.get_all_tasks()

    by_id = {
        task.id: task
        for task in tasks
    }

    children = [
        task
        for task in tasks
        if task.parent_task_id
    ]

    orphaned = [
        task
        for task in children
        if task.parent_task_id not in by_id
    ]

    missing_step = [
        task
        for task in children
        if task.step_order is None
    ]

    nonpositive_step = [
        task
        for task in children
        if (
            task.step_order is not None
            and task.step_order < 1
        )
    ]

    parent_groups: dict[
        str,
        list,
    ] = {}

    for task in children:
        parent_groups.setdefault(
            task.parent_task_id,
            [],
        ).append(task)

    duplicate_steps = []

    for parent_id, group in (
        parent_groups.items()
    ):
        step_values = [
            task.step_order
            for task in group
            if task.step_order is not None
        ]

        duplicates = [
            value
            for value, count
            in Counter(
                step_values
            ).items()
            if count > 1
        ]

        if duplicates:
            duplicate_steps.append({
                "parent_id":
                    parent_id,

                "duplicates":
                    duplicates,
            })

    print(
        f"\nTotal tasks:                 "
        f"{len(tasks)}"
    )

    print(
        f"Tasks with parent:           "
        f"{len(children)}"
    )

    print(
        f"Distinct parents:            "
        f"{len(parent_groups)}"
    )

    print(
        f"Orphaned child links:        "
        f"{len(orphaned)}"
    )

    print(
        f"Children missing step order: "
        f"{len(missing_step)}"
    )

    print(
        f"Legacy missing-step baseline:"
        f" {LEGACY_MISSING_STEP_ORDER_BASELINE}"
    )

    print(
        f"Non-positive step order:     "
        f"{len(nonpositive_step)}"
    )

    print(
        f"Parents with duplicate step: "
        f"{len(duplicate_steps)}"
    )

    failures = []

    if orphaned:
        failures.append(
            f"Orphaned child links: "
            f"{len(orphaned)}"
        )

    if (
        len(missing_step)
        !=
        LEGACY_MISSING_STEP_ORDER_BASELINE
    ):
        failures.append(
            "Missing Step Order count changed "
            "from the verified legacy baseline: "
            f"expected "
            f"{LEGACY_MISSING_STEP_ORDER_BASELINE}, "
            f"found {len(missing_step)}"
        )

    if nonpositive_step:
        failures.append(
            "Non-positive step_order values: "
            f"{len(nonpositive_step)}"
        )

    if duplicate_steps:
        failures.append(
            "Parents with duplicate child "
            f"step_order: "
            f"{len(duplicate_steps)}"
        )

    if failures:
        print(
            "\nRESULT: SUPABASE SUBTASK "
            "RELATIONSHIPS REQUIRE REVIEW"
        )

        for failure in failures:
            print(
                f"  - {failure}"
            )

        raise SystemExit(1)

    print(
        "\nLegacy missing Step Order values "
        "match the verified Notion source."
    )

    print(
        "\nRESULT: SUPABASE SUBTASK "
        "RELATIONSHIPS ARE CLEAN"
    )


if __name__ == "__main__":
    main()