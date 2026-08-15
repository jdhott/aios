from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from aios.models import Task
from aios.storage.execution_repository import ExecutionRepository
from aios.storage.project_repository import ProjectRepository
from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_repository import TaskRepository


def _title_property(
    value: str,
) -> dict[str, Any]:
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


def _select_property(
    value: Optional[str],
) -> dict[str, Any]:
    return {
        "type": "select",
        "select": (
            {"name": value}
            if value
            else None
        ),
    }


def _checkbox_property(
    value: bool,
) -> dict[str, Any]:
    return {
        "type": "checkbox",
        "checkbox": bool(value),
    }


def _date_property(
    value,
) -> dict[str, Any]:
    return {
        "type": "date",
        "date": (
            {
                "start":
                    value.isoformat()
            }
            if value
            else None
        ),
    }


def _number_property(
    value: Optional[int | float],
) -> dict[str, Any]:
    return {
        "type": "number",
        "number": value,
    }


def _rich_text_property(
    value: Optional[str],
) -> dict[str, Any]:
    text = str(
        value or ""
    ).strip()

    return {
        "type": "rich_text",
        "rich_text": (
            [
                {
                    "plain_text": text,
                    "text": {
                        "content": text,
                    },
                }
            ]
            if text
            else []
        ),
    }


def _relation_property(
    relation_id: Optional[str],
) -> dict[str, Any]:
    return {
        "type": "relation",
        "relation": (
            [
                {
                    "id":
                        relation_id
                }
            ]
            if relation_id
            else []
        ),
    }


def _iso_or_none(
    value,
) -> Optional[str]:
    if value is None:
        return None

    if hasattr(
        value,
        "isoformat",
    ):
        return value.isoformat()

    return str(value)


class SupabaseTaskSource:
    """
    Supabase-authoritative task READ compatibility layer.

    The current AIOS cognition/runtime still consumes Notion-shaped task
    dictionaries. This source keeps that interface stable while moving
    authoritative reads to Supabase.

    It intentionally supports only the simple boolean filters and timestamp
    sorts used by the current live runtime. It is NOT a general Notion-query
    translator.
    """

    def __init__(self):
        self.store = SupabaseStore()

        self.task_repository = TaskRepository(
            self.store
        )

        self.project_repository = (
            ProjectRepository(
                self.store
            )
        )

        self.execution_repository = (
            ExecutionRepository(
                self.store
            )
        )

    def _load_context(
        self,
    ):
        tasks = (
            self.task_repository
            .get_all_tasks()
        )

        projects = (
            self.project_repository
            .get_all_projects()
        )

        current_state = (
            self.execution_repository
            .get_current_state()
        )

        task_ref_by_native_id = {
            task.id: (
                task.legacy_notion_id
                or task.id
            )
            for task in tasks
        }

        project_ref_by_native_id = {
            project.id: (
                project.legacy_notion_id
                or project.id
            )
            for project in projects
        }

        return (
            tasks,
            current_state,
            task_ref_by_native_id,
            project_ref_by_native_id,
        )

    def _legacy_payload(
        self,
        task: Task,
        *,
        execution_state: Optional[
            dict[str, Any]
        ] = None,
        task_ref_by_native_id: dict[
            str,
            str,
        ],
        project_ref_by_native_id: dict[
            str,
            str,
        ],
    ) -> dict[str, Any]:
        state = execution_state or {}

        parent_ref = (
            task_ref_by_native_id.get(
                task.parent_task_id
            )
            if task.parent_task_id
            else None
        )

        project_ref = (
            project_ref_by_native_id.get(
                task.project_id
            )
            if task.project_id
            else None
        )

        created_time = _iso_or_none(
            task.created_at
        )

        updated_time = (
            _iso_or_none(
                task.updated_at
            )
            or created_time
        )

        payload = {
            "id": (
                task.legacy_notion_id
                or task.id
            ),
            "_supabase_id":
                task.id,
            "_source":
                "supabase",
            "created_time":
                created_time,
            "last_edited_time":
                updated_time,
            "properties": {
                "Task Name":
                    _title_property(
                        task.title
                    ),
                "Open Loop":
                    _checkbox_property(
                        task.is_open
                    ),
                "Done":
                    _checkbox_property(
                        task.is_done
                    ),
                "Archived":
                    _checkbox_property(
                        task.is_archived
                    ),
                "Status":
                    _select_property(
                        task.status
                    ),
                "Importance":
                    _select_property(
                        task.importance
                    ),
                "Urgency":
                    _select_property(
                        task.urgency
                    ),
                "Effort":
                    _select_property(
                        task.effort
                    ),
                "Duration":
                    _select_property(
                        task.duration
                    ),
                "Due Date":
                    _date_property(
                        task.due_at
                    ),
                "Defer Until":
                    _date_property(
                        task.defer_until
                    ),
                "Just Do It":
                    _checkbox_property(
                        task.is_just_do_it
                    ),
                "Quick Win":
                    _checkbox_property(
                        task.is_quick_win
                    ),
                "Suggested Project":
                    _rich_text_property(
                        task.suggested_project
                    ),
                "Task Role":
                    _rich_text_property(
                        task.task_role
                    ),
                "Project":
                    _relation_property(
                        project_ref
                    ),
                "Parent Task":
                    _relation_property(
                        parent_ref
                    ),
                "Step Order":
                    _number_property(
                        task.step_order
                    ),
                "Execution Score":
                    _number_property(
                        state.get(
                            "execution_score"
                        )
                    ),
                "Execution Rank":
                    _number_property(
                        state.get(
                            "execution_rank"
                        )
                    ),
                "Best Next Action":
                    _checkbox_property(
                        bool(
                            state.get(
                                "best_next_action",
                                False,
                            )
                        )
                    ),
                "Surfaced Quick Win":
                    _checkbox_property(
                        bool(
                            state.get(
                                "surfaced_quick_win",
                                False,
                            )
                        )
                    ),
            },
        }

        # Preserve migrated legacy metadata as a diagnostic-only side channel.
        # Canonical runtime properties above remain authoritative.
        payload[
            "_legacy_metadata"
        ] = (
            task.legacy_metadata
            or {}
        )

        return payload

    @staticmethod
    def _bool_filter_map(
        filter_payload: Optional[
            dict[str, Any]
        ],
    ) -> dict[str, bool]:
        """
        Parse only the simple checkbox equality filters used by the live AIOS
        runtime.

        Supported property names:
          Open Loop
          Done
          Archived
          Just Do It
          Quick Win
        """

        if not filter_payload:
            return {}

        clauses = []

        if (
            isinstance(
                filter_payload,
                dict,
            )
            and "and"
            in filter_payload
        ):
            clauses = (
                filter_payload.get(
                    "and"
                )
                or []
            )

        elif isinstance(
            filter_payload,
            dict,
        ):
            clauses = [
                filter_payload
            ]

        supported = {
            "Open Loop",
            "Done",
            "Archived",
            "Just Do It",
            "Quick Win",
        }

        result: dict[str, bool] = {}

        for clause in clauses:
            if not isinstance(
                clause,
                dict,
            ):
                raise ValueError(
                    "Unsupported Supabase task "
                    "filter clause."
                )

            property_name = (
                clause.get(
                    "property"
                )
            )

            checkbox = (
                clause.get(
                    "checkbox"
                )
            )

            if (
                property_name
                not in supported
                or not isinstance(
                    checkbox,
                    dict,
                )
                or "equals"
                not in checkbox
            ):
                raise ValueError(
                    "Supabase task read supports "
                    "only current AIOS checkbox "
                    "equality filters. "
                    f"Unsupported clause: "
                    f"{clause!r}"
                )

            result[
                property_name
            ] = bool(
                checkbox[
                    "equals"
                ]
            )

        return result

    @staticmethod
    def _matches(
        task: Task,
        filters: dict[
            str,
            bool,
        ],
    ) -> bool:
        mapping = {
            "Open Loop":
                bool(
                    task.is_open
                ),
            "Done":
                bool(
                    task.is_done
                ),
            "Archived":
                bool(
                    task.is_archived
                ),
            "Just Do It":
                bool(
                    task.is_just_do_it
                ),
            "Quick Win":
                bool(
                    task.is_quick_win
                ),
        }

        return all(
            mapping[name]
            == expected
            for (
                name,
                expected,
            )
            in filters.items()
        )

    @staticmethod
    def _sort_tasks(
        tasks: list[Task],
        sorts: Optional[
            list[dict[str, Any]]
        ],
    ) -> list[Task]:
        if not sorts:
            return list(tasks)

        result = list(tasks)

        # Stable sorts applied in reverse priority order.
        for sort in reversed(
            sorts
        ):
            if not isinstance(
                sort,
                dict,
            ):
                raise ValueError(
                    "Unsupported Supabase "
                    "task sort."
                )

            timestamp = sort.get(
                "timestamp"
            )

            direction = str(
                sort.get(
                    "direction",
                    "ascending",
                )
            ).strip().lower()

            reverse = (
                direction
                == "descending"
            )

            if timestamp == "created_time":
                key_fn = lambda task: (
                    task.created_at
                    or datetime.min.replace(
                        tzinfo=timezone.utc
                    )
                )

            elif timestamp == "last_edited_time":
                key_fn = lambda task: (
                    task.updated_at
                    or task.created_at
                    or datetime.min.replace(
                        tzinfo=timezone.utc
                    )
                )

            else:
                raise ValueError(
                    "Supabase task read supports "
                    "only created_time and "
                    "last_edited_time sorts. "
                    f"Unsupported sort: "
                    f"{sort!r}"
                )

            result.sort(
                key=key_fn,
                reverse=reverse,
            )

        return result

    def query_legacy(
        self,
        *,
        filter_payload: Optional[
            dict[str, Any]
        ] = None,
        sorts: Optional[
            list[dict[str, Any]]
        ] = None,
        page_size: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Return the current live query population in legacy task shape.

        `page_size` is accepted for Notion-call compatibility but intentionally
        does NOT truncate results. The existing Notion pagination helper also
        returns every matching row regardless of page size.
        """

        (
            tasks,
            current_state,
            task_ref_by_native_id,
            project_ref_by_native_id,
        ) = self._load_context()

        filters = (
            self._bool_filter_map(
                filter_payload
            )
        )

        filtered = [
            task
            for task in tasks
            if self._matches(
                task,
                filters,
            )
        ]

        filtered = (
            self._sort_tasks(
                filtered,
                sorts,
            )
        )

        payloads = [
            self._legacy_payload(
                task,
                execution_state=(
                    current_state.get(
                        task.id,
                        {},
                    )
                ),
                task_ref_by_native_id=(
                    task_ref_by_native_id
                ),
                project_ref_by_native_id=(
                    project_ref_by_native_id
                ),
            )
            for task in filtered
        ]

        print(
            "[Task Source] "
            "Loaded tasks from Supabase: "
            f"{len(payloads)} "
            f"(filters={filters or 'none'}, "
            f"page_size_compat={page_size})"
        )

        return payloads

    def runtime_open_tasks(
        self,
    ) -> list[dict[str, Any]]:
        # Preserve the existing get_open_tasks() semantics exactly:
        # Open Loop=True, Done=False, with NO Archived filter.
        return self.query_legacy(
            filter_payload={
                "and": [
                    {
                        "property":
                            "Open Loop",
                        "checkbox": {
                            "equals":
                                True,
                        },
                    },
                    {
                        "property":
                            "Done",
                        "checkbox": {
                            "equals":
                                False,
                        },
                    },
                ]
            },
            page_size=100,
        )

    def quick_win_candidate_tasks(
        self,
    ) -> list[dict[str, Any]]:
        return self.query_legacy(
            filter_payload={
                "and": [
                    {
                        "property":
                            "Open Loop",
                        "checkbox": {
                            "equals":
                                True,
                        },
                    },
                    {
                        "property":
                            "Done",
                        "checkbox": {
                            "equals":
                                False,
                        },
                    },
                    {
                        "property":
                            "Archived",
                        "checkbox": {
                            "equals":
                                False,
                        },
                    },
                    {
                        "property":
                            "Just Do It",
                        "checkbox": {
                            "equals":
                                False,
                        },
                    },
                ]
            },
            sorts=[
                {
                    "timestamp":
                        "created_time",
                    "direction":
                        "ascending",
                }
            ],
            page_size=100,
        )


_SOURCE: SupabaseTaskSource | None = None


def get_task_source() -> SupabaseTaskSource:
    global _SOURCE

    if _SOURCE is None:
        _SOURCE = (
            SupabaseTaskSource()
        )

    return _SOURCE


def get_supabase_runtime_open_tasks():
    return (
        get_task_source()
        .runtime_open_tasks()
    )


def get_supabase_quick_win_candidate_tasks():
    return (
        get_task_source()
        .quick_win_candidate_tasks()
    )


def query_supabase_tasks_legacy(
    *,
    filter_payload=None,
    sorts=None,
    page_size=100,
):
    return (
        get_task_source()
        .query_legacy(
            filter_payload=filter_payload,
            sorts=sorts,
            page_size=page_size,
        )
    )
