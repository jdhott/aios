"""
Controlled smoke test for Supabase-primary task creation.

This test:
1. Inserts a temporary task into Supabase.
2. Uses a fake in-memory Notion mirror response.
3. Links the fake legacy ID.
4. Verifies the linkage.
5. Deletes the temporary Supabase task.

It makes NO Notion writes and leaves NO Supabase row behind.

Run:
    python -m scripts.supabase_task_creation_write_smoke
"""

from __future__ import annotations

from uuid import uuid4

from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_creation_writer import SupabasePrimaryTaskCreator


def main() -> None:
    store = SupabaseStore()
    creator = SupabasePrimaryTaskCreator()

    fake_notion_id = str(uuid4())
    title = "AIOS temporary Supabase creation smoke test"

    def fake_notion_create(
        task_title,
        **kwargs,
    ):
        return {
            "id": fake_notion_id,
            "archived": False,
            "properties": {
                "Task Name": {
                    "type": "title",
                    "title": [
                        {
                            "plain_text": task_title,
                            "text": {
                                "content": task_title,
                            },
                        }
                    ],
                },
                "Open Loop": {
                    "type": "checkbox",
                    "checkbox": True,
                },
                "Done": {
                    "type": "checkbox",
                    "checkbox": False,
                },
                "Just Do It": {
                    "type": "checkbox",
                    "checkbox": False,
                },
                "Effort": {
                    "type": "select",
                    "select": {
                        "name": "Small Effort",
                    },
                },
            },
        }

    page = creator.create(
        task_title=title,
        is_jdi=False,
        is_urgent=False,
        is_important=False,
        due_date=None,
        manual_project="",
        notion_create_fn=fake_notion_create,
    )

    if not page:
        raise RuntimeError(
            "Creator returned no page."
        )

    supabase_id = page.get(
        "_supabase_id"
    )

    if not supabase_id:
        raise RuntimeError(
            "Creator returned no Supabase ID."
        )

    result = (
        store.client
        .table("tasks")
        .select(
            "id, legacy_notion_id, title, effort"
        )
        .eq("id", supabase_id)
        .limit(1)
        .execute()
    )

    rows = result.data or []

    if len(rows) != 1:
        raise RuntimeError(
            "Temporary Supabase task not found."
        )

    row = rows[0]

    if row.get("legacy_notion_id") != fake_notion_id:
        raise RuntimeError(
            "Temporary task legacy ID was not linked."
        )

    if row.get("title") != title:
        raise RuntimeError(
            "Temporary task title mismatch."
        )

    if row.get("effort") != "Small Effort":
        raise RuntimeError(
            "Mirror metadata was not synchronized."
        )

    (
        store.client
        .table("tasks")
        .delete()
        .eq("id", supabase_id)
        .execute()
    )

    check = (
        store.client
        .table("tasks")
        .select("id")
        .eq("id", supabase_id)
        .execute()
    )

    if check.data:
        raise RuntimeError(
            "Temporary Supabase task was not cleaned up."
        )

    print(
        "Supabase-primary task creation smoke test passed. "
        "Temporary row was linked and removed; no Notion write occurred."
    )


if __name__ == "__main__":
    main()
