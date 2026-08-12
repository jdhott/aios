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

    Converts Supabase rows into datastore-neutral Task models.

    Collection reads are paginated because Supabase/PostgREST may
    limit the number of rows returned by a single request.
    """

    PAGE_SIZE = 1000

    def __init__(self, store: SupabaseStore):
        self.store = store

    # ------------------------------------------------------------------
    # Row conversion
    # ------------------------------------------------------------------

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
            suggested_project=row.get(
                "suggested_project"
            ),
            project_id=row.get("project_id"),
            parent_task_id=row.get("parent_task_id"),
            step_order=row.get("step_order"),
            legacy_metadata=(
                row.get("legacy_metadata")
                or {}
            ),
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

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get_all_tasks(self) -> list[Task]:
        """
        Return every task in Supabase.

        Results are fetched in pages so datasets larger than the
        Supabase/PostgREST per-request limit are not truncated.
        """

        rows: list[dict[str, Any]] = []

        start = 0

        while True:
            response = (
                self.store.client
                .table("tasks")
                .select("*")
                .order("created_at")
                .range(
                    start,
                    start + self.PAGE_SIZE - 1,
                )
                .execute()
            )

            batch = response.data or []

            rows.extend(batch)

            if len(batch) < self.PAGE_SIZE:
                break

            start += self.PAGE_SIZE

        return [
            self.row_to_task(row)
            for row in rows
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
        """
        Return all currently eligible open tasks.

        Open-task semantics intentionally preserve the current AIOS
        definition:

            is_open = True
            is_done = False
            is_archived = False

        Results are paginated.
        """

        rows: list[dict[str, Any]] = []

        start = 0

        while True:
            response = (
                self.store.client
                .table("tasks")
                .select("*")
                .eq("is_open", True)
                .eq("is_done", False)
                .eq("is_archived", False)
                .order("created_at")
                .range(
                    start,
                    start + self.PAGE_SIZE - 1,
                )
                .execute()
            )

            batch = response.data or []

            rows.extend(batch)

            if len(batch) < self.PAGE_SIZE:
                break

            start += self.PAGE_SIZE

        return [
            self.row_to_task(row)
            for row in rows
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

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def upsert_task(
        self,
        task: Task,
    ) -> Task:
        payload = {
            "legacy_notion_id": task.legacy_notion_id,
            "title": task.title,
            "is_open": task.is_open,
            "is_done": task.is_done,
            "is_archived": task.is_archived,
            "status": task.status,
            "importance": task.importance,
            "urgency": task.urgency,
            "effort": task.effort,
            "duration": task.duration,
            "due_at": (
                task.due_at.isoformat()
                if task.due_at
                else None
            ),
            "defer_until": (
                task.defer_until.isoformat()
                if task.defer_until
                else None
            ),
            "is_just_do_it": task.is_just_do_it,
            "is_quick_win": task.is_quick_win,
            "suggested_project": task.suggested_project,
            "project_id": task.project_id,
            "parent_task_id": task.parent_task_id,
            "step_order": task.step_order,
            "legacy_metadata": task.legacy_metadata,
            "created_at": (
                task.created_at.isoformat()
                if task.created_at
                else None
            ),
            "updated_at": (
                task.updated_at.isoformat()
                if task.updated_at
                else None
            ),
            "completed_at": (
                task.completed_at.isoformat()
                if task.completed_at
                else None
            ),
        }

        response = (
            self.store.client
            .table("tasks")
            .upsert(
                payload,
                on_conflict="legacy_notion_id",
            )
            .execute()
        )

        if not response.data:
            raise RuntimeError(
                f"Failed to upsert task: {task.title}"
            )

        return self.row_to_task(
            response.data[0]
        )

    def update_parent_task(
        self,
        task_id: str,
        parent_task_id: Optional[str],
    ) -> None:
        (
            self.store.client
            .table("tasks")
            .update({
                "parent_task_id": parent_task_id,
            })
            .eq("id", task_id)
            .execute()
        )