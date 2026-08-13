"""
Read-only validation for Supabase task title/lifecycle state.

Run:
    python -m scripts.supabase_task_lifecycle_validate
"""

from __future__ import annotations

from collections import Counter

from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_repository import TaskRepository


def main() -> None:
    print("=" * 72)
    print("AIOS SUPABASE TASK LIFECYCLE VALIDATION")
    print("=" * 72)
    print("\nREAD ONLY.")

    repo = TaskRepository(
        SupabaseStore()
    )

    tasks = repo.get_all_tasks()
    open_tasks = repo.get_open_tasks()

    empty_titles = [
        task.id
        for task in tasks
        if not task.title.strip()
    ]

    completed_without_done = [
        task.id
        for task in tasks
        if (
            task.completed_at is not None
            and not task.is_done
        )
    ]

    lifecycle_counts = Counter(
        (
            task.is_open,
            task.is_done,
            task.is_archived,
        )
        for task in tasks
    )

    failures = []

    if len(tasks) != 1590:
        failures.append(
            f"Expected 1590 tasks; found {len(tasks)}"
        )

    if len(open_tasks) != 277:
        failures.append(
            f"Expected 277 open tasks; found {len(open_tasks)}"
        )

    if empty_titles:
        failures.append(
            f"Tasks with empty titles: {len(empty_titles)}"
        )

    if completed_without_done:
        failures.append(
            "Tasks have completed_at while Done=False: "
            f"{len(completed_without_done)}"
        )

    print(f"\nTotal tasks:                 {len(tasks)}")
    print(f"Open tasks:                  {len(open_tasks)}")
    print(f"Empty titles:                {len(empty_titles)}")
    print(
        "completed_at with Done=False: "
        f"{len(completed_without_done)}"
    )

    print("\nLifecycle combinations:")

    for state, count in sorted(
        lifecycle_counts.items(),
        key=lambda item: -item[1],
    ):
        print(
            f"  Open={state[0]:<5} "
            f"Done={state[1]:<5} "
            f"Archived={state[2]:<5} "
            f"count={count}"
        )

    if failures:
        print("\nRESULT: SUPABASE TASK LIFECYCLE VALIDATION FAILED")
        for failure in failures:
            print(f"  - {failure}")
        raise SystemExit(1)

    print("\nRESULT: SUPABASE TASK LIFECYCLE STRUCTURE IS CLEAN")


if __name__ == "__main__":
    main()
