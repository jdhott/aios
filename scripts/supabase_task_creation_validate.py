"""
Read-only validation of Supabase-primary / Notion-mirrored task creation.

Every persisted Supabase task must have a unique legacy_notion_id, and every
legacy_notion_id in Supabase must still exist in the Notion Tasks database.

Notion may contain extra tasks during the transitional period because
breakdown/clarification creation has not yet migrated.

Run:
    python -m scripts.supabase_task_creation_validate
"""

from __future__ import annotations

from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_repository import TaskRepository

from scripts.supabase_poc_import import (
    TASKS_DATABASE_ID,
    query_database,
)


def main() -> None:
    print("=" * 72)
    print("AIOS SUPABASE-PRIMARY TASK CREATION VALIDATION")
    print("=" * 72)
    print("\nREAD ONLY.")

    repo = TaskRepository(
        SupabaseStore()
    )

    tasks = repo.get_all_tasks()
    notion_pages = query_database(
        TASKS_DATABASE_ID
    )

    supabase_legacy_ids = [
        task.legacy_notion_id
        for task in tasks
        if task.legacy_notion_id
    ]

    missing_legacy = [
        task.id
        for task in tasks
        if not task.legacy_notion_id
    ]

    duplicate_count = (
        len(supabase_legacy_ids)
        - len(set(supabase_legacy_ids))
    )

    notion_ids = {
        page.get("id")
        for page in notion_pages
        if page.get("id")
    }

    supabase_ids_not_in_notion = (
        set(supabase_legacy_ids)
        - notion_ids
    )

    print(
        f"\nSupabase tasks:                  {len(tasks)}"
    )
    print(
        f"Notion tasks:                    {len(notion_pages)}"
    )
    print(
        f"Supabase rows missing legacy ID: {len(missing_legacy)}"
    )
    print(
        f"Duplicate legacy IDs:            {duplicate_count}"
    )
    print(
        "Supabase legacy IDs absent "
        f"from Notion:            {len(supabase_ids_not_in_notion)}"
    )

    failures = []

    if len(tasks) < 1590:
        failures.append(
            f"Supabase task count unexpectedly below baseline: {len(tasks)}"
        )

    if missing_legacy:
        failures.append(
            f"Supabase tasks missing legacy Notion ID: {len(missing_legacy)}"
        )

    if duplicate_count:
        failures.append(
            f"Duplicate legacy Notion IDs: {duplicate_count}"
        )

    if supabase_ids_not_in_notion:
        failures.append(
            "Some Supabase task mirrors are missing from Notion: "
            f"{len(supabase_ids_not_in_notion)}"
        )

    if failures:
        print(
            "\nRESULT: SUPABASE-PRIMARY TASK CREATION VALIDATION FAILED"
        )
        for failure in failures:
            print(f"  - {failure}")
        raise SystemExit(1)

    print(
        "\nRESULT: SUPABASE-PRIMARY TASK CREATION LINKS ARE CLEAN"
    )


if __name__ == "__main__":
    main()
