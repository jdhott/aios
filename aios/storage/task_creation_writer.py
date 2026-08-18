from __future__ import annotations

from typing import Any, Callable, Optional

from aios.storage.supabase_store import SupabaseStore


NotionCreateFn = Callable[..., Optional[dict[str, Any]]]
NotionRollbackFn = Callable[[str, dict[str, Any]], Any]


def _select_or_status_name(
    props: dict[str, Any],
    name: str,
) -> Optional[str]:
    prop = props.get(name, {})

    select = prop.get("select")
    if isinstance(select, dict):
        return select.get("name")

    status = prop.get("status")
    if isinstance(status, dict):
        return status.get("name")

    return None


def _checkbox(
    props: dict[str, Any],
    name: str,
    default: bool = False,
) -> bool:
    prop = props.get(name, {})
    if "checkbox" not in prop:
        return default
    return bool(prop.get("checkbox"))


def _date_start(
    props: dict[str, Any],
    name: str,
) -> Optional[str]:
    prop = props.get(name, {})
    value = prop.get("date")
    if isinstance(value, dict):
        return value.get("start")
    return None


def _rich_text(
    props: dict[str, Any],
    name: str,
) -> Optional[str]:
    prop = props.get(name, {})
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


class SupabasePrimaryTaskCreator:
    """Create an ordinary top-level task directly in authoritative Supabase.

    New native tasks intentionally have no Notion mirror.  The returned value
    keeps the legacy Notion-shaped task interface used by the current runtime,
    but its identity is the native Supabase UUID.
    """

    def __init__(self):
        self.store = SupabaseStore()

    @staticmethod
    def _compat_page(row: dict[str, Any]) -> dict[str, Any]:
        def select_prop(value):
            return {"type": "select", "select": ({"name": value} if value else None)}

        def checkbox_prop(value):
            return {"type": "checkbox", "checkbox": bool(value)}

        def date_prop(value):
            return {"type": "date", "date": ({"start": value} if value else None)}

        suggested = str(row.get("suggested_project") or "").strip()
        rich_text = ([{"plain_text": suggested, "text": {"content": suggested}}] if suggested else [])
        task_id = str(row["id"])
        title = str(row.get("title") or "")
        return {
            "id": task_id,
            "_supabase_id": task_id,
            "_source": "supabase",
            "archived": bool(row.get("is_archived", False)),
            "properties": {
                "Task Name": {"type": "title", "title": [{"plain_text": title, "text": {"content": title}}]},
                "Open Loop": checkbox_prop(row.get("is_open", True)),
                "Done": checkbox_prop(row.get("is_done", False)),
                "Just Do It": checkbox_prop(row.get("is_just_do_it", False)),
                "Status": select_prop(row.get("status")),
                "Importance": select_prop(row.get("importance")),
                "Urgency": select_prop(row.get("urgency")),
                "Effort": select_prop(row.get("effort")),
                "Due Date": date_prop(row.get("due_at")),
                "Suggested Project": {"type": "rich_text", "rich_text": rich_text},
                "Parent Task": {
                    "type": "relation",
                    "relation": ([{"id": str(row["parent_task_id"])}] if row.get("parent_task_id") else []),
                },
                "Step Order": {"type": "number", "number": row.get("step_order")},
            },
        }

    def create(
        self,
        *,
        task_title: str,
        is_jdi: bool,
        is_urgent: bool,
        is_important: bool,
        due_date,
        manual_project: str,
        effort: Optional[str] = None,
        importance: Optional[str] = None,
        status: Optional[str] = None,
        notion_create_fn: Optional[NotionCreateFn] = None,
        notion_rollback_fn: Optional[NotionRollbackFn] = None,
    ) -> Optional[dict[str, Any]]:
        # notion_* arguments remain temporarily accepted so callers/tests can
        # migrate without changing the public creation boundary in one jump.
        del notion_create_fn, notion_rollback_fn

        payload: dict[str, Any] = {
            "legacy_notion_id": None,
            "title": task_title,
            "is_open": True,
            "is_done": False,
            "is_archived": False,
            "is_just_do_it": bool(is_jdi),
            "is_quick_win": False,
            "status": status,
            "urgency": "High Urgency" if is_urgent else None,
            "importance": importance or ("High Importance" if is_important else None),
            "effort": effort,
            "due_at": due_date.isoformat() if due_date else None,
            "suggested_project": manual_project or None,
        }

        response = self.store.client.table("tasks").insert(payload).execute()
        rows = response.data or []
        if not rows:
            raise RuntimeError("Supabase task creation returned no row.")

        row = dict(payload)
        row.update(rows[0])
        print("[Task Creation] Created native Supabase task: " + str(row["id"]))
        return self._compat_page(row)


_CREATOR: SupabasePrimaryTaskCreator | None = None


def create_supabase_primary_task(
    *,
    task_title: str,
    is_jdi: bool,
    is_urgent: bool,
    is_important: bool,
    due_date,
    manual_project: str,
    notion_create_fn: Optional[NotionCreateFn] = None,
    notion_rollback_fn: Optional[NotionRollbackFn] = None,
    effort: Optional[str] = None,
    importance: Optional[str] = None,
    status: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    global _CREATOR

    if _CREATOR is None:
        _CREATOR = SupabasePrimaryTaskCreator()

    return _CREATOR.create(
        task_title=task_title,
        is_jdi=is_jdi,
        is_urgent=is_urgent,
        is_important=is_important,
        due_date=due_date,
        manual_project=manual_project,
        notion_create_fn=notion_create_fn,
        notion_rollback_fn=notion_rollback_fn,
        effort=effort,
        importance=importance,
        status=status,
    )


class SupabasePrimaryTaskHierarchyCreator:
    """Create a breakdown parent and ordered subtasks directly in Supabase.

    New native hierarchies intentionally have no Notion mirrors. Supabase owns
    parent/child identity, parent_task_id, and step_order. Returned task objects
    keep the compatibility shape used by the current processor.
    """

    def __init__(self):
        self.store = SupabaseStore()

    def _delete_task(self, task_id: str) -> None:
        self.store.client.table("tasks").delete().eq("id", task_id).execute()

    def _insert_task(
        self,
        *,
        title: str,
        is_jdi: bool,
        is_urgent: bool,
        is_important: bool,
        due_date,
        manual_project: str,
        parent_task_id: Optional[str],
        step_order: Optional[int],
        project_id: Optional[str] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "legacy_notion_id": None,
            "title": title,
            "is_open": True,
            "is_done": False,
            "is_archived": False,
            "is_just_do_it": bool(is_jdi),
            "is_quick_win": False,
            "urgency": "High Urgency" if is_urgent else None,
            "importance": "High Importance" if is_important else None,
            "due_at": due_date.isoformat() if due_date else None,
            "suggested_project": manual_project or None,
            "project_id": project_id,
            "parent_task_id": parent_task_id,
            "step_order": step_order,
        }
        response = self.store.client.table("tasks").insert(payload).execute()
        rows = response.data or []
        if not rows:
            raise RuntimeError("Supabase hierarchy insert returned no row.")
        row = dict(payload)
        row.update(rows[0])
        return row

    def create_hierarchy(
        self,
        *,
        parent_title: str,
        subtasks: list[str],
        is_jdi: bool,
        is_urgent: bool,
        is_important: bool,
        due_date,
        manual_project: str,
        post_create_fn: Callable[[dict[str, Any], bool], dict[str, Any]],
        notion_create_fn: Optional[NotionCreateFn] = None,
        notion_rollback_fn: Optional[NotionRollbackFn] = None,
    ) -> list[dict[str, Any]]:
        """Preserve breakdown inheritance while creating only native rows."""
        del notion_create_fn, notion_rollback_fn
        created_supabase_ids: list[str] = []
        pages: list[dict[str, Any]] = []

        try:
            parent_row = self._insert_task(
                title=parent_title, is_jdi=is_jdi, is_urgent=is_urgent,
                is_important=is_important, due_date=due_date,
                manual_project=manual_project, parent_task_id=None, step_order=None,
            )
            parent_id = str(parent_row["id"])
            created_supabase_ids.append(parent_id)
            parent_page = SupabasePrimaryTaskCreator._compat_page(parent_row)
            parent_page = post_create_fn(parent_page, is_important)
            pages.append(parent_page)

            for step_order, subtask_title in enumerate(subtasks, start=1):
                child_row = self._insert_task(
                    title=subtask_title, is_jdi=is_jdi, is_urgent=is_urgent,
                    is_important=False, due_date=due_date,
                    manual_project=manual_project, parent_task_id=parent_id,
                    step_order=step_order,
                )
                child_id = str(child_row["id"])
                created_supabase_ids.append(child_id)
                child_page = SupabasePrimaryTaskCreator._compat_page(child_row)
                child_page = post_create_fn(child_page, False)
                pages.append(child_page)

            print(
                "[Task Hierarchy Creation] Created native Supabase parent + "
                f"{len(subtasks)} subtasks without Notion mirrors"
            )
            return pages
        except Exception:
            for task_id in reversed(created_supabase_ids):
                try:
                    self._delete_task(task_id)
                except Exception:
                    pass
            raise


    def create_children_for_existing_parent(
        self,
        *,
        parent_task_id: str,
        subtasks: list[str],
    ) -> list[dict[str, Any]]:
        """Create ordered native children for an existing authoritative task."""
        parent_rows = (
            self.store.client.table("tasks")
            .select(
                "id,title,is_open,is_done,is_archived,is_just_do_it,urgency,"
                "due_at,suggested_project,project_id"
            )
            .eq("id", parent_task_id)
            .limit(1)
            .execute().data
            or []
        )
        if not parent_rows:
            raise RuntimeError("Breakdown parent task was not found.")
        parent = dict(parent_rows[0])
        if parent.get("is_done") or parent.get("is_archived") or not parent.get("is_open"):
            raise RuntimeError("Closed tasks cannot be broken down.")

        existing_children = (
            self.store.client.table("tasks")
            .select("id")
            .eq("parent_task_id", parent_task_id)
            .eq("is_archived", False)
            .limit(1)
            .execute().data
            or []
        )
        if existing_children:
            raise RuntimeError("Task already has breakdown children.")

        created_ids: list[str] = []
        pages: list[dict[str, Any]] = []
        try:
            for step_order, title in enumerate(subtasks, start=1):
                row = self._insert_task(
                    title=title,
                    is_jdi=bool(parent.get("is_just_do_it")),
                    is_urgent=parent.get("urgency") == "High Urgency",
                    is_important=False,
                    due_date=None,
                    manual_project=str(parent.get("suggested_project") or ""),
                    parent_task_id=parent_task_id,
                    step_order=step_order,
                    project_id=(str(parent.get("project_id")) if parent.get("project_id") else None),
                )
                # Preserve the parent's due timestamp exactly when present.
                if parent.get("due_at"):
                    (
                        self.store.client.table("tasks")
                        .update({"due_at": parent.get("due_at")})
                        .eq("id", row["id"])
                        .execute()
                    )
                    row["due_at"] = parent.get("due_at")
                created_ids.append(str(row["id"]))
                pages.append(SupabasePrimaryTaskCreator._compat_page(row))
            return pages
        except Exception:
            for task_id in reversed(created_ids):
                try:
                    self._delete_task(task_id)
                except Exception:
                    pass
            raise


_HIERARCHY_CREATOR: SupabasePrimaryTaskHierarchyCreator | None = None


def create_supabase_primary_hierarchy(
    *,
    parent_title: str,
    subtasks: list[str],
    is_jdi: bool,
    is_urgent: bool,
    is_important: bool,
    due_date,
    manual_project: str,
    post_create_fn: Callable[
        [dict[str, Any], bool],
        dict[str, Any],
    ],
    notion_create_fn: Optional[NotionCreateFn] = None,
    notion_rollback_fn: Optional[NotionRollbackFn] = None,
) -> list[dict[str, Any]]:
    global _HIERARCHY_CREATOR

    if _HIERARCHY_CREATOR is None:
        _HIERARCHY_CREATOR = (
            SupabasePrimaryTaskHierarchyCreator()
        )

    return _HIERARCHY_CREATOR.create_hierarchy(
        parent_title=parent_title,
        subtasks=subtasks,
        is_jdi=is_jdi,
        is_urgent=is_urgent,
        is_important=is_important,
        due_date=due_date,
        manual_project=manual_project,
        notion_create_fn=notion_create_fn,
        post_create_fn=post_create_fn,
        notion_rollback_fn=notion_rollback_fn,
    )


def create_supabase_children_for_existing_parent(
    *,
    parent_task_id: str,
    subtasks: list[str],
) -> list[dict[str, Any]]:
    global _HIERARCHY_CREATOR
    if _HIERARCHY_CREATOR is None:
        _HIERARCHY_CREATOR = SupabasePrimaryTaskHierarchyCreator()
    cleaned = [str(item or "").strip() for item in subtasks if str(item or "").strip()]
    if len(cleaned) < 2:
        raise ValueError("A breakdown requires at least two subtasks.")
    return _HIERARCHY_CREATOR.create_children_for_existing_parent(
        parent_task_id=parent_task_id,
        subtasks=cleaned[:5],
    )
