"""
Idempotent smoke test for existing-task metadata writes to Supabase.

It writes one task's CURRENT metadata values back to the same row and verifies
that the row remains unchanged semantically.

Run:
    python -m scripts.supabase_task_metadata_write_smoke
"""

from __future__ import annotations

from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_repository import TaskRepository
from aios.storage.task_metadata_writer import SupabaseTaskMetadataWriter


def select_prop(value):
    return {
        "select": {"name": value} if value else None,
    }


def checkbox_prop(value):
    return {
        "checkbox": bool(value),
    }


def date_prop(value):
    return {
        "date": (
            {"start": value.isoformat()}
            if value
            else None
        ),
    }


def main() -> None:
    store = SupabaseStore()
    repo = TaskRepository(store)
    writer = SupabaseTaskMetadataWriter()

    candidate = next(
        (
            task
            for task in repo.get_all_tasks()
            if task.legacy_notion_id
        ),
        None,
    )

    if candidate is None:
        raise RuntimeError(
            "No migrated task with legacy_notion_id found."
        )

    before = {
        "importance": candidate.importance,
        "urgency": candidate.urgency,
        "effort": candidate.effort,
        "duration": candidate.duration,
        "due_at": candidate.due_at,
        "defer_until": candidate.defer_until,
        "is_just_do_it": candidate.is_just_do_it,
        "is_quick_win": candidate.is_quick_win,
    }

    legacy_task = {
        "id": candidate.legacy_notion_id,
        "properties": {},
    }

    updates = {
        "Importance": select_prop(candidate.importance),
        "Urgency": select_prop(candidate.urgency),
        "Effort": select_prop(candidate.effort),
        "Duration": select_prop(candidate.duration),
        "Due Date": date_prop(candidate.due_at),
        "Defer Until": date_prop(candidate.defer_until),
        "Just Do It": checkbox_prop(candidate.is_just_do_it),
        "Quick Win": checkbox_prop(candidate.is_quick_win),
    }

    writer.update(
        legacy_task,
        updates,
    )

    after_task = repo.get_task(candidate.id)

    if after_task is None:
        raise RuntimeError(
            "Task missing after metadata smoke test."
        )

    after = {
        "importance": after_task.importance,
        "urgency": after_task.urgency,
        "effort": after_task.effort,
        "duration": after_task.duration,
        "due_at": after_task.due_at,
        "defer_until": after_task.defer_until,
        "is_just_do_it": after_task.is_just_do_it,
        "is_quick_win": after_task.is_quick_win,
    }

    if before != after:
        print("Before:", before)
        print("After: ", after)
        raise RuntimeError(
            "Metadata smoke test changed semantic values."
        )

    print(
        "Supabase existing-task metadata write smoke test passed. "
        "All tested values were preserved."
    )


if __name__ == "__main__":
    main()
