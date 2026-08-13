"""
Idempotent smoke test for Supabase-only task -> project relation writes.

Selects an existing task with a project and writes the same project relation
back to Supabase. No Notion write occurs.

Run:
    python -m scripts.supabase_project_relation_supabase_only_smoke
"""

from __future__ import annotations

from aios.storage.project_repository import ProjectRepository
from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_project_relation_writer import (
    SupabaseProjectRelationWriter,
)
from aios.storage.task_repository import TaskRepository


def main() -> None:
    store = SupabaseStore()
    task_repo = TaskRepository(store)
    project_repo = ProjectRepository(store)

    candidate = next(
        (
            task
            for task in task_repo.get_all_tasks()
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
            "Candidate project cannot be mapped."
        )

    original_project_id = candidate.project_id

    writer = SupabaseProjectRelationWriter()

    _, written_project_id = writer.write_supabase(
        notion_task_id=candidate.legacy_notion_id,
        notion_project_id=project.legacy_notion_id,
    )

    refreshed = task_repo.get_task(
        candidate.id
    )

    if refreshed is None:
        raise RuntimeError(
            "Task missing after smoke test."
        )

    if refreshed.project_id != original_project_id:
        raise RuntimeError(
            "Project relation changed unexpectedly."
        )

    if written_project_id != original_project_id:
        raise RuntimeError(
            "Writer resolved the wrong project."
        )

    print(
        "Supabase-only project relation smoke test passed. "
        "Existing relation was preserved."
    )


if __name__ == "__main__":
    main()
