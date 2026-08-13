"""
Idempotent Supabase-only smoke test for Project task-state writers.

This test performs two safe writes using EXISTING values:
1. writes an existing non-empty Suggested Project value back to the same task;
2. writes an existing task -> project relation back to the same task.

No Notion write occurs and no logical state should change.

Run:
    python -m scripts.supabase_project_task_state_write_smoke
"""

from __future__ import annotations

from aios.storage.project_repository import ProjectRepository
from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_metadata_writer import update_task_metadata
from aios.storage.task_project_relation_writer import (
    SupabaseProjectRelationWriter,
)
from aios.storage.task_repository import TaskRepository
from aios.storage.task_source import query_supabase_tasks_legacy


def _rich_text(value: str) -> dict:
    return {
        "rich_text": [
            {
                "type": "text",
                "text": {
                    "content": value,
                },
                "plain_text": value,
            }
        ]
    }


def _notion_write_forbidden(*args, **kwargs):
    raise RuntimeError(
        "Notion update function was called during "
        "Supabase-only smoke test."
    )


def main() -> None:
    store = SupabaseStore()
    task_repo = TaskRepository(store)
    project_repo = ProjectRepository(store)

    all_tasks = task_repo.get_all_tasks()

    suggested_candidate = next(
        (
            task
            for task in all_tasks
            if (
                task.legacy_notion_id
                and str(
                    task.suggested_project
                    or ""
                ).strip()
            )
        ),
        None,
    )

    if suggested_candidate is None:
        raise RuntimeError(
            "No task with an existing Suggested Project "
            "value is available for idempotent smoke testing."
        )

    payloads = query_supabase_tasks_legacy(
        page_size=100,
    )

    legacy_task = next(
        (
            item
            for item in payloads
            if item.get("_supabase_id")
            == suggested_candidate.id
        ),
        None,
    )

    if legacy_task is None:
        raise RuntimeError(
            "Could not build legacy payload for "
            "Suggested Project smoke candidate."
        )

    original_suggested = (
        str(
            suggested_candidate.suggested_project
            or ""
        ).strip()
    )

    updated_payload = update_task_metadata(
        legacy_task,
        {
            "Suggested Project":
                _rich_text(
                    original_suggested
                )
        },
        datastore="supabase",
        notion_update_fn=_notion_write_forbidden,
    )

    refreshed_suggested = task_repo.get_task(
        suggested_candidate.id
    )

    if refreshed_suggested is None:
        raise RuntimeError(
            "Suggested Project candidate disappeared."
        )

    if (
        refreshed_suggested.suggested_project
        != original_suggested
    ):
        raise RuntimeError(
            "Suggested Project changed unexpectedly."
        )

    updated_rich_text = (
        updated_payload
        .get(
            "properties",
            {},
        )
        .get(
            "Suggested Project",
            {},
        )
        .get(
            "rich_text",
            [],
        )
    )

    updated_text = "".join(
        item.get(
            "plain_text",
            "",
        )
        or item.get(
            "text",
            {},
        ).get(
            "content",
            "",
        )
        for item in updated_rich_text
    ).strip()

    if updated_text != original_suggested:
        raise RuntimeError(
            "Updated runtime payload did not retain "
            "Suggested Project."
        )

    relation_candidate = next(
        (
            task
            for task in all_tasks
            if (
                task.project_id
                and task.legacy_notion_id
            )
        ),
        None,
    )

    if relation_candidate is None:
        raise RuntimeError(
            "No existing task/project relation available "
            "for idempotent smoke testing."
        )

    project = project_repo.get_project(
        relation_candidate.project_id
    )

    if (
        project is None
        or not project.legacy_notion_id
    ):
        raise RuntimeError(
            "Relation smoke project cannot be mapped."
        )

    original_project_id = (
        relation_candidate.project_id
    )

    writer = SupabaseProjectRelationWriter()

    _, written_project_id = writer.write_supabase(
        notion_task_id=relation_candidate.legacy_notion_id,
        notion_project_id=project.legacy_notion_id,
    )

    refreshed_relation = task_repo.get_task(
        relation_candidate.id
    )

    if refreshed_relation is None:
        raise RuntimeError(
            "Relation candidate disappeared."
        )

    if (
        refreshed_relation.project_id
        != original_project_id
    ):
        raise RuntimeError(
            "Project relation changed unexpectedly."
        )

    if written_project_id != original_project_id:
        raise RuntimeError(
            "Relation writer resolved the wrong project."
        )

    print(
        "Suggested Project idempotent Supabase write: PASS"
    )
    print(
        "Task -> Project relation idempotent Supabase write: PASS"
    )
    print(
        "No Notion update path invoked."
    )
    print(
        "\nRESULT: PROJECT TASK-STATE "
        "WRITE SMOKE TEST PASSED"
    )


if __name__ == "__main__":
    main()
