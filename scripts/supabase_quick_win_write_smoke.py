"""
Idempotent smoke test for the Supabase Quick Win task-metadata write path.

This writes one task's existing is_quick_win value back to the same row,
then reads it back. No semantic state is changed.

Run:
    python -m scripts.supabase_quick_win_write_smoke
"""

from __future__ import annotations

from aios.storage.execution_state_writer import QuickWinSupabaseWriter
from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_repository import TaskRepository


def main() -> None:
    store = SupabaseStore()
    repo = TaskRepository(store)

    tasks = repo.get_all_tasks()

    candidate = next(
        (
            task
            for task in tasks
            if task.legacy_notion_id
        ),
        None,
    )

    if candidate is None:
        raise RuntimeError(
            "No task with legacy_notion_id found."
        )

    original = bool(candidate.is_quick_win)

    writer = QuickWinSupabaseWriter()

    properties = {
        "Quick Win": {
            "type": "checkbox",
            "checkbox": original,
        }
    }

    writer(candidate.legacy_notion_id, properties)
    writer(candidate.id, properties)

    refreshed = repo.get_task(candidate.id)

    if refreshed is None:
        raise RuntimeError(
            "Task disappeared after smoke test."
        )

    if bool(refreshed.is_quick_win) != original:
        raise RuntimeError(
            "Quick Win value changed unexpectedly."
        )

    print(
        "Supabase Quick Win identity smoke test passed. "
        "Legacy and native task IDs both preserved the existing value."
    )


if __name__ == "__main__":
    main()
