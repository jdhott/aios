"""
Controlled smoke test for Supabase-primary parent/subtask creation.

Creates a temporary parent and two children in Supabase, uses fake Notion
mirror IDs, validates parent_task_id and step_order, then deletes all temporary
rows. No real Notion writes occur.

Run:
    python -m scripts.supabase_subtask_creation_write_smoke
"""

from __future__ import annotations

from uuid import uuid4

from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_creation_writer import (
    SupabasePrimaryTaskHierarchyCreator,
)


def fake_page(
    title: str,
    page_id: str,
):
    return {
        "id": page_id,
        "archived": False,
        "properties": {
            "Task Name": {
                "type": "title",
                "title": [
                    {
                        "plain_text": title,
                        "text": {
                            "content": title,
                        },
                    }
                ],
            },
        },
    }


def main() -> None:
    store = SupabaseStore()
    creator = (
        SupabasePrimaryTaskHierarchyCreator()
    )

    fake_ids = [
        str(uuid4()),
        str(uuid4()),
        str(uuid4()),
    ]

    call_index = 0

    def fake_notion_create(
        task_title,
        **kwargs,
    ):
        nonlocal call_index

        page_id = fake_ids[
            call_index
        ]
        call_index += 1

        return fake_page(
            task_title,
            page_id,
        )

    def no_op_post_create(
        page,
        explicit_important,
    ):
        return page

    pages = creator.create_hierarchy(
        parent_title=(
            "AIOS temporary hierarchy smoke parent"
        ),
        subtasks=[
            "AIOS temporary hierarchy child one",
            "AIOS temporary hierarchy child two",
        ],
        is_jdi=False,
        is_urgent=False,
        is_important=False,
        due_date=None,
        manual_project="",
        notion_create_fn=fake_notion_create,
        post_create_fn=no_op_post_create,
    )

    if len(pages) != 3:
        raise RuntimeError(
            f"Expected 3 pages; found {len(pages)}"
        )

    ids = [
        page["_supabase_id"]
        for page in pages
    ]

    response = (
        store.client
        .table("tasks")
        .select(
            "id, legacy_notion_id, "
            "parent_task_id, step_order, title"
        )
        .in_("id", ids)
        .execute()
    )

    rows = response.data or []

    if len(rows) != 3:
        raise RuntimeError(
            f"Expected 3 rows; found {len(rows)}"
        )

    by_id = {
        row["id"]: row
        for row in rows
    }

    parent_id = pages[0][
        "_supabase_id"
    ]
    child_one_id = pages[1][
        "_supabase_id"
    ]
    child_two_id = pages[2][
        "_supabase_id"
    ]

    if (
        by_id[parent_id]
        .get("parent_task_id")
        is not None
    ):
        raise RuntimeError(
            "Parent unexpectedly has a parent."
        )

    if (
        by_id[child_one_id]
        .get("parent_task_id")
        != parent_id
    ):
        raise RuntimeError(
            "Child one parent link is incorrect."
        )

    if (
        by_id[child_two_id]
        .get("parent_task_id")
        != parent_id
    ):
        raise RuntimeError(
            "Child two parent link is incorrect."
        )

    if (
        by_id[child_one_id]
        .get("step_order")
        != 1
    ):
        raise RuntimeError(
            "Child one step_order is incorrect."
        )

    if (
        by_id[child_two_id]
        .get("step_order")
        != 2
    ):
        raise RuntimeError(
            "Child two step_order is incorrect."
        )

    if {
        row["legacy_notion_id"]
        for row in rows
    } != set(fake_ids):
        raise RuntimeError(
            "Legacy mirror IDs are incorrect."
        )

    for task_id in [
        child_two_id,
        child_one_id,
        parent_id,
    ]:
        (
            store.client
            .table("tasks")
            .delete()
            .eq("id", task_id)
            .execute()
        )

    check = (
        store.client
        .table("tasks")
        .select("id")
        .in_("id", ids)
        .execute()
    )

    if check.data:
        raise RuntimeError(
            "Temporary hierarchy rows were not removed."
        )

    print(
        "Supabase-primary hierarchy creation smoke test passed. "
        "Parent links and step order were correct; "
        "temporary rows were removed."
    )


if __name__ == "__main__":
    main()
