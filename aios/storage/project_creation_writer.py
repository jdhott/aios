from __future__ import annotations

from typing import Any, Optional

from aios.storage.supabase_store import SupabaseStore


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


class SupabaseProjectCreator:
    """
    Create project-emergence stubs directly in Supabase.

    No Notion project page is created.

    The returned object deliberately keeps the legacy Notion-shaped project
    surface expected by aios.projects, but its `id` is the native Supabase
    project UUID and `legacy_notion_id` remains null in the database.

    Project cognition remains outside this class.
    """

    def __init__(self):
        self.store = SupabaseStore()

    def create(
        self,
        *,
        project_name: str,
        status_value: str,
        source_reason: str = "",
    ) -> dict[str, Any]:
        project_name = str(
            project_name or ""
        ).strip()

        if not project_name:
            raise ValueError(
                "Project name cannot be empty."
            )

        response = (
            self.store.client
            .table("projects")
            .insert({
                "legacy_notion_id": None,
                "name": project_name,
                "status": status_value,
                "is_active": False,
            })
            .execute()
        )

        rows = response.data or []

        if not rows:
            raise RuntimeError(
                "Supabase project creation returned no row."
            )

        row = rows[0]
        project_id = row["id"]

        print(
            "[Project Creation] "
            "Created Supabase-only project: "
            f"{project_name} ({project_id})"
        )

        return {
            "id": project_id,
            "_supabase_id": project_id,
            "_source": "supabase",
            "_source_reason": source_reason,
            "properties": {
                "Project Name":
                    _title_property(
                        row.get("name")
                        or project_name
                    ),
                "Status":
                    _select_property(
                        row.get("status")
                        or status_value
                    ),
                "Active":
                    _checkbox_property(
                        bool(
                            row.get(
                                "is_active",
                                False,
                            )
                        )
                    ),
            },
        }


_CREATOR: SupabaseProjectCreator | None = None


def create_supabase_project(
    *,
    project_name: str,
    status_value: str,
    source_reason: str = "",
) -> dict[str, Any]:
    global _CREATOR

    if _CREATOR is None:
        _CREATOR = SupabaseProjectCreator()

    return _CREATOR.create(
        project_name=project_name,
        status_value=status_value,
        source_reason=source_reason,
    )
