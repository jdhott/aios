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
    """
    Create an ordinary top-level task in Supabase first, then create a temporary
    Notion mirror and link the two through tasks.legacy_notion_id.

    This creator intentionally does NOT handle:
      - subtasks / Parent Task
      - Step Order
      - clarification tasks
      - project relations

    Those paths remain on the existing Notion creation flow until their
    relationship semantics are migrated.
    """

    def __init__(self):
        self.store = SupabaseStore()

    def _delete_supabase_task(
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

    def create(
        self,
        *,
        task_title: str,
        is_jdi: bool,
        is_urgent: bool,
        is_important: bool,
        due_date,
        manual_project: str,
        notion_create_fn: NotionCreateFn,
        notion_rollback_fn: Optional[NotionRollbackFn] = None,
    ) -> Optional[dict[str, Any]]:
        """
        Create Supabase row -> Notion mirror -> link legacy_notion_id.

        If Notion creation fails, the Supabase row is deleted.
        If linking the mirror back to Supabase fails, the Notion page is
        archived when a rollback callback is supplied and the Supabase row is
        deleted.
        """

        initial_payload: dict[str, Any] = {
            "legacy_notion_id": None,
            "title": task_title,
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
        }

        response = (
            self.store.client
            .table("tasks")
            .insert(initial_payload)
            .execute()
        )

        rows = response.data or []

        if not rows:
            raise RuntimeError(
                "Supabase task creation returned no row."
            )

        supabase_task_id = rows[0]["id"]

        print(
            "[Task Creation] "
            f"Created Supabase task first: {supabase_task_id}"
        )

        try:
            page = notion_create_fn(
                task_title,
                is_jdi=is_jdi,
                is_urgent=is_urgent,
                is_important=is_important,
                due_date=due_date,
                parent_task_id=None,
                step_order=None,
                manual_project=manual_project,
            )

            if not page or not page.get("id"):
                self._delete_supabase_task(
                    supabase_task_id
                )
                print(
                    "[Task Creation] "
                    "Notion mirror failed; rolled back Supabase task."
                )
                return None

            notion_id = page["id"]
            props = page.get(
                "properties",
                {},
            )

            # Capture the actual metadata written by the existing Notion
            # creation path (notably Effort and inferred Importance) so the
            # newly-created Supabase task begins in parity with its mirror.
            mirror_payload = {
                "legacy_notion_id": notion_id,
                "title": task_title,
                "is_open": _checkbox(
                    props,
                    "Open Loop",
                    True,
                ),
                "is_done": _checkbox(
                    props,
                    "Done",
                    False,
                ),
                "is_archived": bool(
                    page.get("archived", False)
                ),
                "status": _select_or_status_name(
                    props,
                    "Status",
                ),
                "importance": _select_or_status_name(
                    props,
                    "Importance",
                ),
                "urgency": _select_or_status_name(
                    props,
                    "Urgency",
                ),
                "effort": _select_or_status_name(
                    props,
                    "Effort",
                ),
                "due_at": _date_start(
                    props,
                    "Due Date",
                ),
                "is_just_do_it": _checkbox(
                    props,
                    "Just Do It",
                    is_jdi,
                ),
                "suggested_project": (
                    _rich_text(
                        props,
                        "Suggested Project",
                    )
                    or (
                        manual_project
                        if manual_project
                        else None
                    )
                ),
            }

            link_response = (
                self.store.client
                .table("tasks")
                .update(mirror_payload)
                .eq("id", supabase_task_id)
                .execute()
            )

            if not (link_response.data or []):
                raise RuntimeError(
                    "Failed to link Notion mirror "
                    "to newly-created Supabase task."
                )

            page["_supabase_id"] = (
                supabase_task_id
            )
            page["_source"] = "supabase"

            print(
                "[Task Creation] "
                "Linked Notion mirror "
                f"{notion_id} -> Supabase {supabase_task_id}"
            )

            return page

        except Exception:
            # Compensating rollback: do not leave a new authoritative
            # Supabase task without a valid mirror during this stage.
            try:
                self._delete_supabase_task(
                    supabase_task_id
                )
            except Exception:
                pass

            page_id = (
                locals().get("page", {})
                or {}
            ).get("id")

            if (
                page_id
                and notion_rollback_fn
            ):
                try:
                    notion_rollback_fn(
                        page_id,
                        {
                            "Archived": {
                                "checkbox": True,
                            }
                        },
                    )
                except Exception:
                    pass

            raise


_CREATOR: SupabasePrimaryTaskCreator | None = None


def create_supabase_primary_task(
    *,
    task_title: str,
    is_jdi: bool,
    is_urgent: bool,
    is_important: bool,
    due_date,
    manual_project: str,
    notion_create_fn: NotionCreateFn,
    notion_rollback_fn: Optional[NotionRollbackFn] = None,
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
