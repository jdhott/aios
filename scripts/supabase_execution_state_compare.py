"""
Compare current Notion execution state to Supabase task_execution_state.

READ ONLY.

Run:
    python -m scripts.supabase_execution_state_compare
"""

from __future__ import annotations

from typing import Any

from aios.storage.execution_repository import ExecutionRepository
from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_repository import TaskRepository

from scripts.supabase_poc_import import (
    TASKS_DATABASE_ID,
    query_database,
)


def notion_number(props: dict[str, Any], name: str):
    prop = props.get(name, {})
    if prop.get("type") != "number":
        return None
    return prop.get("number")


def notion_checkbox(props: dict[str, Any], name: str) -> bool:
    prop = props.get(name, {})
    if prop.get("type") != "checkbox":
        return False
    return prop.get("checkbox") is True


def main() -> None:
    print("=" * 72)
    print("AIOS EXECUTION STATE NOTION / SUPABASE COMPARISON")
    print("=" * 72)
    print("\nREAD ONLY.")

    pages = query_database(TASKS_DATABASE_ID)

    current_notion: dict[str, dict[str, Any]] = {}

    for page in pages:
        props = page.get("properties", {})

        if notion_checkbox(props, "Done"):
            continue

        rank = notion_number(props, "Execution Rank")
        surfaced = notion_checkbox(props, "Surfaced Quick Win")

        if rank is None and not surfaced:
            continue

        current_notion[page["id"]] = {
            "execution_score": (
                notion_number(props, "Execution Score")
                if rank is not None
                else None
            ),
            "execution_rank": rank,
            "best_next_action": (
                rank is not None
                and rank <= 5
            ),
            "surfaced_quick_win": surfaced,
        }

    store = SupabaseStore()
    task_repo = TaskRepository(store)
    execution_repo = ExecutionRepository(store)

    notion_to_supabase = {
        task.legacy_notion_id: task.id
        for task in task_repo.get_all_tasks()
        if task.legacy_notion_id
    }

    expected: dict[str, dict[str, Any]] = {}

    missing = []

    for notion_id, state in current_notion.items():
        task_id = notion_to_supabase.get(notion_id)

        if not task_id:
            missing.append(notion_id)
            continue

        expected[task_id] = state

    stored_raw = execution_repo.get_current_state()

    actual = {
        task_id: {
            "execution_score": row.get("execution_score"),
            "execution_rank": row.get("execution_rank"),
            "best_next_action": bool(
                row.get("best_next_action", False)
            ),
            "surfaced_quick_win": bool(
                row.get("surfaced_quick_win", False)
            ),
        }
        for task_id, row in stored_raw.items()
    }

    expected_ids = set(expected)
    actual_ids = set(actual)

    only_notion = expected_ids - actual_ids
    only_supabase = actual_ids - expected_ids

    changed = [
        task_id
        for task_id in expected_ids & actual_ids
        if expected[task_id] != actual[task_id]
    ]

    print(f"\nNotion current-state rows:   {len(expected)}")
    print(f"Supabase current-state rows: {len(actual)}")
    print(f"Missing task mappings:       {len(missing)}")
    print(f"Only in Notion:              {len(only_notion)}")
    print(f"Only in Supabase:            {len(only_supabase)}")
    print(f"Different rows:              {len(changed)}")

    if missing or only_notion or only_supabase or changed:
        print("\nRESULT: EXECUTION STATE PARITY FAILED")
        raise SystemExit(1)

    print("\nRESULT: EXACT EXECUTION STATE PARITY")


if __name__ == "__main__":
    main()
