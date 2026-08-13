"""
Offline smoke test for SupabasePrimaryTaskCreator with a clarification task.

This test uses an in-memory fake Supabase client and fake Notion mirror.
It performs NO network or production database writes.

It proves that the existing Supabase-first creator can:
- create a clarification-shaped task;
- create/link a Notion mirror;
- capture Status=Needs Clarification into Supabase mirror metadata;
- return a legacy-shaped page carrying _supabase_id and _source.

Run:
    python -m scripts.supabase_clarification_creation_smoke
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aios.storage.task_creation_writer import (
    SupabasePrimaryTaskCreator,
)


@dataclass
class FakeResponse:
    data: list[dict[str, Any]]


class FakeTable:
    def __init__(
        self,
        state: dict[str, Any],
    ):
        self.state = state
        self.pending_insert = None
        self.pending_update = None
        self.eq_value = None

    def insert(
        self,
        payload,
    ):
        self.pending_insert = dict(payload)
        return self

    def update(
        self,
        payload,
    ):
        self.pending_update = dict(payload)
        return self

    def delete(self):
        self.state["deleted"] = True
        return self

    def eq(
        self,
        field,
        value,
    ):
        self.eq_value = (
            field,
            value,
        )
        return self

    def execute(self):
        if self.pending_insert is not None:
            self.state["insert_payload"] = (
                self.pending_insert
            )
            return FakeResponse(
                data=[
                    {
                        "id":
                            "supabase-clarify-1",
                        **self.pending_insert,
                    }
                ]
            )

        if self.pending_update is not None:
            self.state["update_payload"] = (
                self.pending_update
            )
            return FakeResponse(
                data=[
                    {
                        "id":
                            "supabase-clarify-1",
                        **self.pending_update,
                    }
                ]
            )

        if self.state.get("deleted"):
            return FakeResponse(data=[])

        return FakeResponse(data=[])


class FakeClient:
    def __init__(
        self,
        state,
    ):
        self.state = state

    def table(
        self,
        name,
    ):
        if name != "tasks":
            raise AssertionError(
                f"Unexpected table: {name}"
            )
        return FakeTable(
            self.state
        )


class FakeStore:
    def __init__(
        self,
        state,
    ):
        self.client = FakeClient(
            state
        )


def title_prop(
    text,
):
    return {
        "type":
            "title",
        "title": [
            {
                "plain_text":
                    text,
                "text": {
                    "content":
                        text,
                },
            }
        ],
    }


def checkbox_prop(
    value,
):
    return {
        "type":
            "checkbox",
        "checkbox":
            bool(value),
    }


def select_prop(
    value,
):
    return {
        "type":
            "select",
        "select": (
            {
                "name":
                    value
            }
            if value
            else None
        ),
    }


def fake_notion_create(
    task_title,
    *,
    is_jdi,
    is_urgent,
    is_important,
    due_date,
    parent_task_id,
    step_order,
    manual_project,
):
    if not task_title.lower().startswith(
        "clarify next action:"
    ):
        raise AssertionError(
            "Smoke test did not receive a "
            "clarification task title."
        )

    if parent_task_id is not None:
        raise AssertionError(
            "Clarification task unexpectedly "
            "received a parent."
        )

    if step_order is not None:
        raise AssertionError(
            "Clarification task unexpectedly "
            "received step order."
        )

    return {
        "id":
            "notion-clarify-1",
        "archived":
            False,
        "properties": {
            "Task Name":
                title_prop(
                    task_title
                ),
            "Open Loop":
                checkbox_prop(
                    True
                ),
            "Done":
                checkbox_prop(
                    False
                ),
            "Just Do It":
                checkbox_prop(
                    is_jdi
                ),
            "Status":
                select_prop(
                    "Needs Clarification"
                ),
            "Importance":
                select_prop(
                    "High Importance"
                    if is_important
                    else None
                ),
            "Urgency":
                select_prop(
                    "High Urgency"
                    if is_urgent
                    else None
                ),
            "Effort":
                select_prop(
                    "Low Effort"
                ),
            "Due Date": {
                "type":
                    "date",
                "date":
                    None,
            },
            "Suggested Project": {
                "type":
                    "rich_text",
                "rich_text":
                    [],
            },
        },
    }


def forbidden_rollback(
    *args,
    **kwargs,
):
    raise AssertionError(
        "Rollback should not run "
        "during successful smoke test."
    )


def main() -> None:
    state: dict[str, Any] = {}

    creator = (
        SupabasePrimaryTaskCreator.__new__(
            SupabasePrimaryTaskCreator
        )
    )
    creator.store = FakeStore(
        state
    )

    page = creator.create(
        task_title=(
            "Clarify next action: "
            "Plan garden project"
        ),
        is_jdi=False,
        is_urgent=False,
        is_important=False,
        due_date=None,
        manual_project="",
        notion_create_fn=fake_notion_create,
        notion_rollback_fn=forbidden_rollback,
    )

    if not page:
        raise RuntimeError(
            "Creator returned no page."
        )

    insert_payload = state.get(
        "insert_payload",
        {},
    )

    update_payload = state.get(
        "update_payload",
        {},
    )

    checks = [
        (
            "Supabase row inserted first",
            insert_payload.get(
                "title"
            )
            == (
                "Clarify next action: "
                "Plan garden project"
            ),
        ),
        (
            "Notion mirror linked",
            update_payload.get(
                "legacy_notion_id"
            )
            == "notion-clarify-1",
        ),
        (
            "clarification status captured",
            update_payload.get(
                "status"
            )
            == "Needs Clarification",
        ),
        (
            "open state captured",
            update_payload.get(
                "is_open"
            )
            is True
            and update_payload.get(
                "is_done"
            )
            is False,
        ),
        (
            "returned page carries Supabase identity",
            page.get(
                "_supabase_id"
            )
            == "supabase-clarify-1",
        ),
        (
            "returned page marked Supabase source",
            page.get(
                "_source"
            )
            == "supabase",
        ),
    ]

    failed = [
        label
        for label, ok in checks
        if not ok
    ]

    for label, ok in checks:
        print(
            f"{'PASS' if ok else 'FAIL'}: "
            f"{label}"
        )

    if failed:
        print(
            "\nRESULT: CLARIFICATION CREATION "
            "SMOKE TEST FAILED"
        )
        for label in failed:
            print(
                f"  - {label}"
            )
        raise SystemExit(1)

    print(
        "\nRESULT: CLARIFICATION CREATION "
        "SMOKE TEST PASSED"
    )


if __name__ == "__main__":
    main()
