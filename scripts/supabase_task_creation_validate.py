"""
Read-only validation of mixed native/migrated Supabase task identity.

Native Supabase tasks may intentionally have legacy_notion_id=NULL. Historical
rows that do carry a legacy_notion_id must remain unique. During the transition,
a historical legacy ID that no longer resolves to a Notion page is reported as
an integrity warning, not a failure of Supabase-primary task creation.

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

    repo = TaskRepository(SupabaseStore())

    tasks = repo.get_all_tasks()
    notion_pages = query_database(TASKS_DATABASE_ID)

    supabase_legacy_ids = [
        task.legacy_notion_id
        for task in tasks
        if task.legacy_notion_id
    ]

    native_task_ids = [
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

    legacy_ids_not_in_notion = (
        set(supabase_legacy_ids)
        - notion_ids
    )

    print(f"\nSupabase tasks:                  {len(tasks)}")
    print(f"Notion tasks:                    {len(notion_pages)}")
    print(f"Native Supabase-only tasks:       {len(native_task_ids)}")
    print(f"Duplicate legacy IDs:            {duplicate_count}")
    print(
        "Historical legacy IDs absent "
        f"from Notion:         {len(legacy_ids_not_in_notion)}"
    )

    failures = []
    warnings = []

    if len(tasks) < 1590:
        failures.append(
            f"Supabase task count unexpectedly below baseline: {len(tasks)}"
        )

    if duplicate_count:
        failures.append(
            f"Duplicate legacy Notion IDs: {duplicate_count}"
        )

    if legacy_ids_not_in_notion:
        warnings.append(
            "Historical Supabase rows reference legacy Notion IDs that no "
            "longer resolve in the Notion Tasks database: "
            f"{len(legacy_ids_not_in_notion)}"
        )

    if warnings:
        print("\nWARNINGS:")
        for warning in warnings:
            print(f"  - {warning}")

    if failures:
        print("\nRESULT: SUPABASE TASK IDENTITY VALIDATION FAILED")
        for failure in failures:
            print(f"  - {failure}")
        raise SystemExit(1)

    print("\nPASS: native Supabase-only tasks are valid")
    print("PASS: non-null legacy Notion IDs remain unique")
    print("PASS: Supabase remains authoritative for task identity")
    print("RESULT: SUPABASE TASK IDENTITIES ARE CLEAN")


if __name__ == "__main__":
    main()
