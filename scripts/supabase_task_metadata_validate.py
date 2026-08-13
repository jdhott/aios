"""
Read-only structural validation after the existing-task metadata write cutover.

Run:
    python -m scripts.supabase_task_metadata_validate
"""

from __future__ import annotations

from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_repository import TaskRepository


def main() -> None:
    print("=" * 72)
    print("AIOS SUPABASE TASK METADATA VALIDATION")
    print("=" * 72)
    print("\nREAD ONLY.")

    repo = TaskRepository(
        SupabaseStore()
    )

    tasks = repo.get_all_tasks()
    open_tasks = repo.get_open_tasks()

    notion_ids = [
        task.legacy_notion_id
        for task in tasks
        if task.legacy_notion_id
    ]

    duplicate_legacy_ids = (
        len(notion_ids)
        - len(set(notion_ids))
    )

    quick_wins = sum(
        1
        for task in tasks
        if task.is_quick_win
    )

    jdis = sum(
        1
        for task in tasks
        if task.is_just_do_it
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

    if len(notion_ids) != 1590:
        failures.append(
            "Not every task has a legacy Notion ID."
        )

    if duplicate_legacy_ids:
        failures.append(
            f"Duplicate legacy Notion IDs: {duplicate_legacy_ids}"
        )

    print(f"\nTotal tasks:              {len(tasks)}")
    print(f"Open tasks:               {len(open_tasks)}")
    print(f"Legacy Notion IDs:        {len(notion_ids)}")
    print(f"Duplicate legacy IDs:     {duplicate_legacy_ids}")
    print(f"Quick Win tasks:          {quick_wins}")
    print(f"Just Do It tasks:         {jdis}")

    if failures:
        print("\nRESULT: SUPABASE TASK METADATA VALIDATION FAILED")
        for failure in failures:
            print(f"  - {failure}")
        raise SystemExit(1)

    print("\nRESULT: SUPABASE TASK METADATA STRUCTURE IS CLEAN")


if __name__ == "__main__":
    main()
