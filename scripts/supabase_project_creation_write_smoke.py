"""
Controlled smoke test for Supabase-primary project creation.

This test:
1. Creates a temporary project row in Supabase.
2. Supplies a fake Notion mirror response.
3. Verifies legacy_notion_id / status / active linkage.
4. Deletes the temporary Supabase project.

No real Notion write occurs.

Run:
    python -m scripts.supabase_project_creation_write_smoke
"""

from __future__ import annotations

from uuid import uuid4

from aios.storage.project_creation_writer import (
    SupabasePrimaryProjectCreator,
)
from aios.storage.supabase_store import SupabaseStore


def main() -> None:
    store = SupabaseStore()
    creator = (
        SupabasePrimaryProjectCreator()
    )

    fake_notion_id = str(
        uuid4()
    )

    name = (
        "AIOS temporary project creation smoke test"
    )

    def fake_notion_create(
        project_name,
        existing_projects=None,
        source_reason="",
    ):
        return {
            "id": fake_notion_id,
            "properties": {
                "Project Name": {
                    "type": "title",
                    "title": [
                        {
                            "plain_text":
                                project_name,
                            "text": {
                                "content":
                                    project_name,
                            },
                        }
                    ],
                },
                "Status": {
                    "type": "select",
                    "select": {
                        "name": "Someday",
                    },
                },
                "Active": {
                    "type": "checkbox",
                    "checkbox": False,
                },
            },
        }

    page = creator.create(
        project_name=name,
        status_value="Someday",
        existing_projects=[],
        source_reason="smoke test",
        notion_create_fn=(
            fake_notion_create
        ),
    )

    if not page:
        raise RuntimeError(
            "Project creator returned no page."
        )

    supabase_id = page.get(
        "_supabase_id"
    )

    if not supabase_id:
        raise RuntimeError(
            "Project creator returned "
            "no Supabase ID."
        )

    response = (
        store.client
        .table("projects")
        .select(
            "id, legacy_notion_id, "
            "name, status, is_active"
        )
        .eq(
            "id",
            supabase_id,
        )
        .limit(1)
        .execute()
    )

    rows = response.data or []

    if len(rows) != 1:
        raise RuntimeError(
            "Temporary Supabase project "
            "was not found."
        )

    row = rows[0]

    if (
        row.get("legacy_notion_id")
        != fake_notion_id
    ):
        raise RuntimeError(
            "Project legacy Notion ID "
            "was not linked."
        )

    if row.get("name") != name:
        raise RuntimeError(
            "Project name mismatch."
        )

    if (
        row.get("status")
        != "Someday"
    ):
        raise RuntimeError(
            "Project status mismatch."
        )

    if bool(
        row.get("is_active")
    ):
        raise RuntimeError(
            "Temporary project unexpectedly active."
        )

    (
        store.client
        .table("projects")
        .delete()
        .eq(
            "id",
            supabase_id,
        )
        .execute()
    )

    check = (
        store.client
        .table("projects")
        .select("id")
        .eq(
            "id",
            supabase_id,
        )
        .execute()
    )

    if check.data:
        raise RuntimeError(
            "Temporary project row "
            "was not cleaned up."
        )

    print(
        "Supabase-primary project creation smoke test passed. "
        "Temporary project was linked and removed; "
        "no Notion write occurred."
    )


if __name__ == "__main__":
    main()
