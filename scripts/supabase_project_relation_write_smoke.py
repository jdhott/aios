"""
Idempotent smoke test for Supabase task -> project relation writes.

Selects an existing task that already has a project and writes the same
project_id back to Supabase. No Notion write occurs and semantic state does not
change.

Run:
    python -m scripts.supabase_project_relation_write_smoke
"""

from __future__ import annotations

from aios.storage.project_repository import ProjectRepository
from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_project_relation_writer import (
    SupabasePrimaryProjectRelationWriter,
)
from aios.storage.task_repository import TaskRepository


def main() -> None:
    store = SupabaseStore()

    task_repo = TaskRepository(
        store
    )
    project_repo = ProjectRepository(
        store
    )

    tasks = task_repo.get_all_tasks()

    candidate = next(
        (
            task
            for task in tasks
            if (
                task.project_id
                and task.legacy_notion_id
            )
        ),
        None,
    )

    if candidate is None:
        raise RuntimeError(
            "No existing task/project relation found."
        )

    project = project_repo.get_project(
        candidate.project_id
    )

    if (
        project is None
        or not project.legacy_notion_id
    ):
        raise RuntimeError(
            "Candidate project cannot be mapped "
            "to a legacy Notion project."
        )

    before = candidate.project_id

    writer = (
        SupabasePrimaryProjectRelationWriter()
    )

    _, written_project_id = (
        writer.write_supabase(
            notion_task_id=(
                candidate.legacy_notion_id
            ),
            notion_project_id=(
                project.legacy_notion_id
            ),
        )
    )

    refreshed = task_repo.get_task(
        candidate.id
    )

    if refreshed is None:
        raise RuntimeError(
            "Task missing after relation smoke test."
        )

    if refreshed.project_id != before:
        raise RuntimeError(
            "Project relation changed unexpectedly."
        )

    if written_project_id != before:
        raise RuntimeError(
            "Writer resolved the wrong Supabase project."
        )

    print(
        "Supabase project relation write smoke test passed. "
        "Existing task/project relation was preserved."
    )


if __name__ == "__main__":
    main()
