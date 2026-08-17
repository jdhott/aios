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
    """
    Create a breakdown parent and ordered subtasks in Supabase first, then
    create temporary Notion mirrors.

    Supabase owns:
      - parent/child identity
      - parent_task_id
      - step_order

    Notion pages remain temporary UI mirrors.
    """

    def __init__(self):
        self.store = SupabaseStore()

    def _delete_task(
        self,
        task_id: str,
    ) -> None:
        (
            self.store.client
            .table("tasks")
            .delete()
            .eq("id", task_id)
            .execute()
        )

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
    ) -> str:
        response = (
            self.store.client
            .table("tasks")
            .insert({
                "legacy_notion_id": None,
                "title": title,
                "is_open": True,
                "is_done": False,
                "is_archived": False,
                "is_just_do_it": bool(is_jdi),
                "is_quick_win": False,
                "urgency": (
                    "High Urgency"
                    if is_urgent
                    else None
                ),
                "importance": (
                    "High Importance"
                    if is_important
                    else None
                ),
                "due_at": (
                    due_date.isoformat()
                    if due_date
                    else None
                ),
                "suggested_project": (
                    manual_project
                    if manual_project
                    else None
                ),
                "parent_task_id": parent_task_id,
                "step_order": step_order,
            })
            .execute()
        )

        rows = response.data or []

        if not rows:
            raise RuntimeError(
                "Supabase hierarchy insert returned no row."
            )

        return rows[0]["id"]

    def _link_mirror(
        self,
        *,
        supabase_task_id: str,
        notion_page: dict[str, Any],
    ) -> None:
        notion_id = notion_page.get("id")

        if not notion_id:
            raise RuntimeError(
                "Notion mirror has no page ID."
            )

        response = (
            self.store.client
            .table("tasks")
            .update({
                "legacy_notion_id": notion_id,
            })
            .eq("id", supabase_task_id)
            .execute()
        )

        if not (response.data or []):
            raise RuntimeError(
                "Failed to link Notion hierarchy mirror."
            )

        notion_page["_supabase_id"] = (
            supabase_task_id
        )
        notion_page["_source"] = "supabase"

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
        notion_create_fn: NotionCreateFn,
        post_create_fn: Callable[
            [dict[str, Any], bool],
            dict[str, Any],
        ],
        notion_rollback_fn: Optional[NotionRollbackFn] = None,
    ) -> list[dict[str, Any]]:
        """
        Preserve the existing breakdown semantics:

        Parent:
          inherits JDI, urgency, importance, due date.

        Children:
          inherit JDI, urgency, due date.
          importance remains non-explicit, matching the current runtime.
        """

        created_supabase_ids: list[str] = []
        created_notion_ids: list[str] = []
        pages: list[dict[str, Any]] = []

        try:
            parent_supabase_id = self._insert_task(
                title=parent_title,
                is_jdi=is_jdi,
                is_urgent=is_urgent,
                is_important=is_important,
                due_date=due_date,
                manual_project=manual_project,
                parent_task_id=None,
                step_order=None,
            )

            created_supabase_ids.append(
                parent_supabase_id
            )

            parent_page = notion_create_fn(
                parent_title,
                is_jdi=is_jdi,
                is_urgent=is_urgent,
                is_important=is_important,
                due_date=due_date,
                parent_task_id=None,
                step_order=None,
                manual_project=manual_project,
            )

            if not parent_page:
                raise RuntimeError(
                    "Parent Notion mirror creation failed."
                )

            self._link_mirror(
                supabase_task_id=parent_supabase_id,
                notion_page=parent_page,
            )

            created_notion_ids.append(
                parent_page["id"]
            )

            parent_page = post_create_fn(
                parent_page,
                is_important,
            )

            parent_page["_supabase_id"] = (
                parent_supabase_id
            )
            parent_page["_source"] = "supabase"

            pages.append(
                parent_page
            )

            parent_notion_id = (
                parent_page["id"]
            )

            for step_order, subtask_title in enumerate(
                subtasks,
                start=1,
            ):
                child_supabase_id = self._insert_task(
                    title=subtask_title,
                    is_jdi=is_jdi,
                    is_urgent=is_urgent,
                    is_important=False,
                    due_date=due_date,
                    manual_project=manual_project,
                    parent_task_id=parent_supabase_id,
                    step_order=step_order,
                )

                created_supabase_ids.append(
                    child_supabase_id
                )

                child_page = notion_create_fn(
                    subtask_title,
                    is_jdi=is_jdi,
                    is_urgent=is_urgent,
                    is_important=False,
                    due_date=due_date,
                    parent_task_id=parent_notion_id,
                    step_order=step_order,
                    manual_project=manual_project,
                )

                if not child_page:
                    raise RuntimeError(
                        "Child Notion mirror creation failed "
                        f"at step {step_order}."
                    )

                self._link_mirror(
                    supabase_task_id=child_supabase_id,
                    notion_page=child_page,
                )

                created_notion_ids.append(
                    child_page["id"]
                )

                child_page = post_create_fn(
                    child_page,
                    False,
                )

                child_page["_supabase_id"] = (
                    child_supabase_id
                )
                child_page["_source"] = "supabase"

                pages.append(
                    child_page
                )

            print(
                "[Task Hierarchy Creation] "
                f"Created parent + {len(subtasks)} subtasks "
                "Supabase-first with linked Notion mirrors"
            )

            return pages

        except Exception:
            if notion_rollback_fn:
                for notion_id in reversed(
                    created_notion_ids
                ):
                    try:
                        notion_rollback_fn(
                            notion_id,
                            {
                                "Archived": {
                                    "checkbox": True,
                                }
                            },
                        )
                    except Exception:
                        pass

            for task_id in reversed(
                created_supabase_ids
            ):
                try:
                    self._delete_task(
                        task_id
                    )
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
    notion_create_fn: NotionCreateFn,
    post_create_fn: Callable[
        [dict[str, Any], bool],
        dict[str, Any],
    ],
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
