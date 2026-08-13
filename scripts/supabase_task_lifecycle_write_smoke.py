"""
Idempotent smoke test for existing-task title/lifecycle writes to Supabase.

The test selects a current non-done task and writes its existing title,
status, Open Loop, Done, and Archived values back unchanged.

Run:
    python -m scripts.supabase_task_lifecycle_write_smoke
"""

from __future__ import annotations

from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_repository import TaskRepository
from aios.storage.task_lifecycle_writer import SupabaseTaskLifecycleWriter


def main() -> None:
    store = SupabaseStore()
    repo = TaskRepository(store)
    writer = SupabaseTaskLifecycleWriter()

    candidate = next(
        (
            task
            for task in repo.get_all_tasks()
            if (
                task.legacy_notion_id
                and not task.is_done
                and not task.is_archived
            )
        ),
        None,
    )

    if candidate is None:
        raise RuntimeError(
            "No suitable migrated task found."
        )

    before = {
        "title": candidate.title,
        "status": candidate.status,
        "is_open": candidate.is_open,
        "is_done": candidate.is_done,
        "is_archived": candidate.is_archived,
        "completed_at": candidate.completed_at,
    }

    writer.update(
        candidate.legacy_notion_id,
        {
            "Task Name": {
                "title": [
                    {
                        "text": {
                            "content": candidate.title
                        }
                    }
                ]
            },
            "Status": {
                "select": (
                    {"name": candidate.status}
                    if candidate.status
                    else None
                )
            },
            "Open Loop": {
                "checkbox": candidate.is_open
            },
            "Done": {
                "checkbox": candidate.is_done
            },
            "Archived": {
                "checkbox": candidate.is_archived
            },
        },
    )

    after_task = repo.get_task(
        candidate.id
    )

    if after_task is None:
        raise RuntimeError(
            "Task missing after lifecycle smoke test."
        )

    after = {
        "title": after_task.title,
        "status": after_task.status,
        "is_open": after_task.is_open,
        "is_done": after_task.is_done,
        "is_archived": after_task.is_archived,
        "completed_at": after_task.completed_at,
    }

    if before != after:
        print("Before:", before)
        print("After: ", after)
        raise RuntimeError(
            "Lifecycle smoke test changed semantic values."
        )

    print(
        "Supabase existing-task lifecycle write smoke test passed. "
        "Title and lifecycle values were preserved."
    )


if __name__ == "__main__":
    main()
