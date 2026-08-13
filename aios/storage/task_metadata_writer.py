from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Callable, Optional

from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_repository import TaskRepository


NotionUpdateFn = Callable[[str, dict[str, Any]], Any]


SUPPORTED_PROPERTIES = {
    "Importance",
    "Urgency",
    "Effort",
    "Duration",
    "Due Date",
    "Defer Until",
    "Just Do It",
    "Quick Win",
    "Suggested Project",
}


def _select_name(prop: dict[str, Any]) -> Optional[str]:
    value = prop.get("select")
    if isinstance(value, dict):
        return value.get("name")
    return None


def _checkbox_value(prop: dict[str, Any]) -> bool:
    return bool(prop.get("checkbox"))


def _date_value(prop: dict[str, Any]) -> Optional[str]:
    value = prop.get("date")
    if isinstance(value, dict):
        return value.get("start")
    return None


def _text_value(prop: dict[str, Any]) -> Optional[str]:
    values = prop.get("rich_text")
    if not isinstance(values, list):
        return None

    text = "".join(
        item.get("plain_text")
        or item.get("text", {}).get("content", "")
        for item in values
        if isinstance(item, dict)
    ).strip()

    return text or None


def _normalize_property(
    name: str,
    prop: dict[str, Any],
) -> dict[str, Any]:
    """
    Return a Notion-shaped property body so downstream legacy helpers can
    continue reading the in-memory task after a Supabase update.
    """
    if name in {
        "Importance",
        "Urgency",
        "Effort",
        "Duration",
    }:
        return {
            "type": "select",
            "select": prop.get("select"),
        }

    if name in {
        "Just Do It",
        "Quick Win",
    }:
        return {
            "type": "checkbox",
            "checkbox": bool(prop.get("checkbox")),
        }

    if name in {
        "Due Date",
        "Defer Until",
    }:
        return {
            "type": "date",
            "date": prop.get("date"),
        }

    if name == "Suggested Project":
        return {
            "type": "rich_text",
            "rich_text": prop.get("rich_text", []),
        }

    return deepcopy(prop)


class SupabaseTaskMetadataWriter:
    """
    Write supported existing-task metadata directly to Supabase.

    The caller still passes legacy Notion-shaped task objects because the
    migration is intentionally incremental. legacy_notion_id is used only to
    locate the corresponding Supabase task UUID.
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
            "[Task Metadata Write] "
            f"Loaded task ID mappings: {len(self._notion_to_supabase)}"
        )

    def _task_id(self, legacy_notion_id: str) -> str:
        self._ensure_map()
        assert self._notion_to_supabase is not None

        task_id = self._notion_to_supabase.get(legacy_notion_id)

        if not task_id:
            raise RuntimeError(
                "Task metadata write could not map Notion task ID "
                f"{legacy_notion_id} to Supabase."
            )

        return task_id

    def _payload(
        self,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        unsupported = set(updates) - SUPPORTED_PROPERTIES

        if unsupported:
            raise ValueError(
                "Unsupported Supabase task metadata properties: "
                + ", ".join(sorted(unsupported))
            )

        payload: dict[str, Any] = {}

        for name, prop in updates.items():
            if not isinstance(prop, dict):
                raise ValueError(
                    f"Invalid property body for {name}: {prop!r}"
                )

            if name == "Importance":
                payload["importance"] = _select_name(prop)

            elif name == "Urgency":
                payload["urgency"] = _select_name(prop)

            elif name == "Effort":
                payload["effort"] = _select_name(prop)

            elif name == "Duration":
                payload["duration"] = _select_name(prop)

            elif name == "Due Date":
                payload["due_at"] = _date_value(prop)

            elif name == "Defer Until":
                payload["defer_until"] = _date_value(prop)

            elif name == "Just Do It":
                payload["is_just_do_it"] = _checkbox_value(prop)

            elif name == "Quick Win":
                payload["is_quick_win"] = _checkbox_value(prop)

            elif name == "Suggested Project":
                payload["suggested_project"] = _text_value(prop)

        return payload

    def update(
        self,
        task: dict[str, Any],
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        if not task:
            raise ValueError("Task metadata update requires a task.")

        legacy_notion_id = task.get("id")

        if not legacy_notion_id:
            raise ValueError(
                "Legacy task payload has no id."
            )

        task_id = self._task_id(legacy_notion_id)
        payload = self._payload(updates)

        if payload:
            (
                self.store.client
                .table("tasks")
                .update(payload)
                .eq("id", task_id)
                .execute()
            )

        # Keep the current runtime object coherent without a Notion refetch.
        updated_task = deepcopy(task)
        props = updated_task.setdefault("properties", {})

        for name, prop in updates.items():
            props[name] = _normalize_property(
                name,
                prop,
            )

        updated_task["_source"] = "supabase"
        updated_task["_supabase_id"] = task_id

        return updated_task


_SUPABASE_WRITER: SupabaseTaskMetadataWriter | None = None


def update_task_metadata(
    task: dict[str, Any],
    updates: dict[str, Any],
    *,
    datastore: str,
    notion_update_fn: NotionUpdateFn,
) -> dict[str, Any]:
    """
    Datastore-aware update for supported metadata on an EXISTING task.

    notion:
        Preserve the existing Notion update behavior.

    supabase:
        Write directly to Supabase and return an updated legacy-shaped
        in-memory task object.
    """
    normalized = datastore.strip().lower()

    if normalized == "notion":
        return notion_update_fn(
            task["id"],
            updates,
        )

    if normalized != "supabase":
        raise ValueError(
            "datastore must be 'notion' or 'supabase'"
        )

    global _SUPABASE_WRITER

    if _SUPABASE_WRITER is None:
        print(
            "[Task Metadata Write] "
            "Supabase existing-task metadata writes active"
        )
        _SUPABASE_WRITER = SupabaseTaskMetadataWriter()

    return _SUPABASE_WRITER.update(
        task,
        updates,
    )
