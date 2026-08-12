from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from aios.models import Task
from aios.storage.supabase_store import SupabaseStore


def parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None

    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


class TaskRepository:
    """
    Supabase persistence layer for AIOS tasks.

    This repository converts database rows into datastore-neutral
    AIOS Task models so the rest of AIOS does not need to know
    about Supabase table structure.
    """

    def __init__(self, store: SupabaseStore):
        self.store = store

    def row_to_task(
        self,
        row: dict[str, Any],
    ) -> Task:
        return Task(
            id=row["id"],
            legacy_notion_id=row.get("legacy_notion_id"),

            title=row.get("title") or "(Untitled Task)",

            is_open=row.get("is_open", True),
            is_done=row.get("is_done", False),
            is_archived=row.get("is_archived", False),

            status=row.get("status"),

            importance=row.get("importance"),
            urgency=row.get("urgency"),
            effort=row.get("effort"),
            duration=row.get("duration"),

            due_at=parse_datetime(
                row.get("due_at")
            ),

            defer_until=parse_datetime(
                row.get("defer_until")
            ),

            is_just_do_it=row.get(
                "is_just_do_it",
                False,
            ),

            is_quick_win=row.get(
                "is_quick_win",
                False,
            ),

            project_id=row.get("project_id"),
            parent_task_id=row.get("parent_task_id"),
            step_order=row.get("step_order"),

            created_at=parse_datetime(
                row.get("created_at")
            ),

            updated_at=parse_datetime(
                row.get("updated_at")
            ),

            completed_at=parse_datetime(
                row.get("completed_at")
            ),
        )

    def get_all_tasks(self) -> list[Task]:
        response = (
            self.store.client
            .table("tasks")
            .select("*")
            .order("created_at")
            .execute()
        )

        return [
            self.row_to_task(row)
            for row in (response.data or [])
        ]

    def get_task(
        self,
        task_id: str,
    ) -> Optional[Task]:
        response = (
            self.store.client
            .table("tasks")
            .select("*")
            .eq("id", task_id)
            .limit(1)
            .execute()
        )

        rows = response.data or []

        if not rows:
            return None

        return self.row_to_task(rows[0])

    def get_task_by_legacy_notion_id(
        self,
        notion_id: str,
    ) -> Optional[Task]:
        response = (
            self.store.client
            .table("tasks")
            .select("*")
            .eq(
                "legacy_notion_id",
                notion_id,
            )
            .limit(1)
            .execute()
        )

        rows = response.data or []

        if not rows:
            return None

        return self.row_to_task(rows[0])

    def get_open_tasks(self) -> list[Task]:
        response = (
            self.store.client
            .table("tasks")
            .select("*")
            .eq("is_open", True)
            .eq("is_done", False)
            .eq("is_archived", False)
            .order("created_at")
            .execute()
        )

        return [
            self.row_to_task(row)
            for row in (response.data or [])
        ]

    def count_tasks(self) -> int:
        response = (
            self.store.client
            .table("tasks")
            .select(
                "id",
                count="exact",
            )
            .execute()
        )

        return response.count or 0