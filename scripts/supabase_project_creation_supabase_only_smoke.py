"""
Controlled smoke test for Supabase-only project creation.

Creates a temporary project in Supabase, verifies that:
- legacy_notion_id is null
- the project read adapter exposes its native Supabase UUID as project["id"]
- the task/project relation writer can resolve that native UUID

Then deletes the temporary project.

No Notion write occurs.

Run:
    python -m scripts.supabase_project_creation_supabase_only_smoke
"""

from __future__ import annotations

from aios.storage.project_creation_writer import (
    SupabaseProjectCreator,
)
from aios.storage.project_source import (
    get_supabase_projects,
)
from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_project_relation_writer import (
    SupabaseProjectRelationWriter,
)


def main() -> None:
    store = SupabaseStore()

    creator = SupabaseProjectCreator()

    page = creator.create(
        project_name=(
            "AIOS temporary Supabase-only project smoke test"
        ),
        status_value="Someday",
        source_reason="smoke test",
    )

    project_id = page["id"]

    row_response = (
        store.client
        .table("projects")
        .select(
            "id, legacy_notion_id, name, status, is_active"
        )
        .eq("id", project_id)
        .limit(1)
        .execute()
    )

    rows = row_response.data or []

    if len(rows) != 1:
        raise RuntimeError(
            "Temporary project row not found."
        )

    row = rows[0]

    if row.get("legacy_notion_id") is not None:
        raise RuntimeError(
            "Supabase-only project unexpectedly has a legacy Notion ID."
        )

    adapted = {
        project["id"]: project
        for project in get_supabase_projects()
    }

    if project_id not in adapted:
        raise RuntimeError(
            "Supabase-only project is invisible to project read adapter."
        )

    writer = SupabaseProjectRelationWriter()

    if writer.resolve_project_id(project_id) != project_id:
        raise RuntimeError(
            "Native Supabase project UUID did not resolve correctly."
        )

    (
        store.client
        .table("projects")
        .delete()
        .eq("id", project_id)
        .execute()
    )

    check = (
        store.client
        .table("projects")
        .select("id")
        .eq("id", project_id)
        .execute()
    )

    if check.data:
        raise RuntimeError(
            "Temporary project row was not removed."
        )

    print(
        "Supabase-only project creation smoke test passed. "
        "Native UUID was readable and relation-resolvable; "
        "temporary project was removed."
    )


if __name__ == "__main__":
    main()
