from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Optional

from aios.models import Task
from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_repository import TaskRepository


NotionUpdateFn = Callable[[str, dict[str, Any]], Any]


SUPPORTED_PROPERTIES = {
    "Task Name",
    "Status",
    "Open Loop",
    "Done",
    "Archived",
}


def _title_value(prop: dict[str, Any]) -> Optional[str]:
    values = prop.get("title")

    if not isinstance(values, list):
        return None

    text = "".join(
        item.get("plain_text")
        or item.get("text", {}).get("content", "")
        for item in values
        if isinstance(item, dict)
    ).strip()

    return text or None


def _select_value(prop: dict[str, Any]) -> Optional[str]:
    value = prop.get("select")

    if not isinstance(value, dict):
        return None

    return value.get("name")


def _checkbox_value(prop: dict[str, Any]) -> bool:
    return bool(prop.get("checkbox"))


def _title_property(value: str) -> dict[str, Any]:
    return {
        "type": "title",
        "title": [
            {
                "plain_text": value,
                "text": {
                    "content": value,
                },
            }
        ],
    }


def _select_property(value: Optional[str]) -> dict[str, Any]:
    return {
        "type": "select",
        "select": (
            {"name": value}
            if value
            else None
        ),
    }


def _checkbox_property(value: bool) -> dict[str, Any]:
    return {
        "type": "checkbox",
        "checkbox": bool(value),
    }


def _date_property(value) -> dict[str, Any]:
    return {
        "type": "date",
        "date": (
            {"start": value.isoformat()}
            if value
            else None
        ),
    }


def _rich_text_property(value: Optional[str]) -> dict[str, Any]:
    return {
        "type": "rich_text",
        "rich_text": (
            [
                {
                    "plain_text": value,
                    "text": {
                        "content": value,
                    },
                }
            ]
            if value
            else []
        ),
    }


def task_to_legacy_payload(task: Task) -> dict[str, Any]:
    """
    Build the Notion-shaped subset still expected by the transitional runtime.
    """
    return {
        "id": task.legacy_notion_id or task.id,
        "_supabase_id": task.id,
        "_source": "supabase",
        "properties": {
            "Task Name": _title_property(task.title),
            "Status": _select_property(task.status),
            "Open Loop": _checkbox_property(task.is_open),
            "Done": _checkbox_property(task.is_done),
            "Archived": _checkbox_property(task.is_archived),
            "Importance": _select_property(task.importance),
            "Urgency": _select_property(task.urgency),
            "Effort": _select_property(task.effort),
            "Duration": _select_property(task.duration),
            "Due Date": _date_property(task.due_at),
            "Defer Until": _date_property(task.defer_until),
            "Just Do It": _checkbox_property(task.is_just_do_it),
            "Quick Win": _checkbox_property(task.is_quick_win),
            "Suggested Project": _rich_text_property(
                task.suggested_project
            ),
        },
    }


class SupabaseTaskLifecycleWriter:
    """
    Write title/status/lifecycle changes on EXISTING tasks to Supabase.

    Supported fields:
      - Task Name
      - Status
      - Open Loop
      - Done
      - Archived

    completed_at is maintained from Done:
      - setting Done=True stamps completed_at if it was previously empty
      - setting Done=False clears completed_at
      - setting Done=True on an already-completed task preserves the timestamp
    """

    def __init__(self):
        self.store = SupabaseStore()
        self.repository = TaskRepository(self.store)
        self._notion_to_supabase: dict[str, str] | None = None

    def _ensure_map(self) -> None:
        if self._notion_to_supabase is not None:
            return

        tasks = self.repository.get_all_tasks()

        self._notion_to_supabase = {
            task.legacy_notion_id: task.id
            for task in tasks
            if task.legacy_notion_id
        }

        print(
            "[Task Lifecycle Write] "
            f"Loaded task ID mappings: {len(self._notion_to_supabase)}"
        )

    def refresh_tasks(self) -> None:
        # Reload task identities after same-process task creation.
        self._notion_to_supabase = None
        self._ensure_map()
        print(
            "[Task Lifecycle Write] Refreshed task ID mappings after cache miss"
        )

    def _task_id(self, legacy_notion_id: str) -> str:
        self._ensure_map()
        assert self._notion_to_supabase is not None

        task_id = self._notion_to_supabase.get(
            legacy_notion_id
        )

        if not task_id:
            self.refresh_tasks()
            assert self._notion_to_supabase is not None
            task_id = self._notion_to_supabase.get(
                legacy_notion_id
            )

        if not task_id:
            raise RuntimeError(
                "Task lifecycle write could not map Notion task ID "
                f"{legacy_notion_id} to Supabase after refresh."
            )

        return task_id

    def update(
        self,
        legacy_notion_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        unsupported = set(updates) - SUPPORTED_PROPERTIES

        if unsupported:
            raise ValueError(
                "Unsupported Supabase lifecycle properties: "
                + ", ".join(sorted(unsupported))
            )

        task_id = self._task_id(
            legacy_notion_id
        )

        current = self.repository.get_task(
            task_id
        )

        if current is None:
            raise RuntimeError(
                f"Supabase task {task_id} not found."
            )

        payload: dict[str, Any] = {}

        for name, prop in updates.items():
            if not isinstance(prop, dict):
                raise ValueError(
                    f"Invalid property body for {name}: {prop!r}"
                )

            if name == "Task Name":
                title = _title_value(prop)

                if not title:
                    raise ValueError(
                        "Task Name cannot be empty."
                    )

                payload["title"] = title

            elif name == "Status":
                payload["status"] = _select_value(prop)

            elif name == "Open Loop":
                payload["is_open"] = _checkbox_value(prop)

            elif name == "Archived":
                payload["is_archived"] = _checkbox_value(prop)

            elif name == "Done":
                done = _checkbox_value(prop)
                payload["is_done"] = done

                if done:
                    payload["completed_at"] = (
                        current.completed_at.isoformat()
                        if current.completed_at
                        else datetime.now(
                            timezone.utc
                        ).isoformat()
                    )
                else:
                    payload["completed_at"] = None

        if payload:
            payload["updated_at"] = datetime.now(
                timezone.utc
            ).isoformat()

            (
                self.store.client
                .table("tasks")
                .update(payload)
                .eq("id", task_id)
                .execute()
            )

        refreshed = self.repository.get_task(
            task_id
        )

        if refreshed is None:
            raise RuntimeError(
                "Task disappeared after lifecycle update."
            )

        return task_to_legacy_payload(
            refreshed
        )


_SUPABASE_WRITER: SupabaseTaskLifecycleWriter | None = None


def update_task_lifecycle(
    legacy_notion_id: str,
    updates: dict[str, Any],
    *,
    datastore: str,
    notion_update_fn: NotionUpdateFn,
) -> dict[str, Any]:
    """
    Datastore-aware update for title/status/lifecycle on an EXISTING task.
    """
    normalized = datastore.strip().lower()

    if normalized == "notion":
        return notion_update_fn(
            legacy_notion_id,
            updates,
        )

    if normalized != "supabase":
        raise ValueError(
            "datastore must be 'notion' or 'supabase'"
        )

    global _SUPABASE_WRITER

    if _SUPABASE_WRITER is None:
        print(
            "[Task Lifecycle Write] "
            "Supabase existing-task title/lifecycle writes active"
        )
        _SUPABASE_WRITER = SupabaseTaskLifecycleWriter()

    return _SUPABASE_WRITER.update(
        legacy_notion_id,
        updates,
    )
