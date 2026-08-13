from __future__ import annotations

from typing import Any, Optional

from aios.storage.project_repository import ProjectRepository
from aios.storage.supabase_store import SupabaseStore


ACTIVE_PROJECT_STATUS_VALUES = {
    "active",
    "in progress",
    "current",
    "ongoing",
}

INACTIVE_PROJECT_STATUS_VALUES = {
    "completed",
    "done",
    "archived",
    "paused",
    "someday",
}


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


def _legacy_select(
    metadata: dict[str, Any],
    key: str,
) -> dict[str, Any]:
    value = metadata.get(key)

    return _select_property(
        str(value)
        if value not in {
            None,
            "",
        }
        else None
    )


def project_to_legacy_payload(
    project,
) -> dict[str, Any]:
    """
    Convert a datastore-neutral Supabase Project into the temporary
    Notion-shaped object expected by aios.projects.

    Only Project Name, Status and Active are operationally required by the
    current matcher. Selected legacy metadata is also exposed so diagnostics
    remain useful during migration.
    """
    metadata = (
        getattr(
            project,
            "legacy_metadata",
            None,
        )
        or {}
    )

    return {
        "id": (
            getattr(
                project,
                "legacy_notion_id",
                None,
            )
            or project.id
        ),
        "_supabase_id": project.id,
        "_source": "supabase",
        "properties": {
            "Project Name":
                _title_property(
                    project.name
                ),
            "Status":
                _select_property(
                    project.status
                ),
            "Active":
                _checkbox_property(
                    bool(
                        project.is_active
                    )
                ),
            "Area":
                _legacy_select(
                    metadata,
                    "area",
                ),
            "Priority":
                _legacy_select(
                    metadata,
                    "priority",
                ),
            "Project Type":
                _legacy_select(
                    metadata,
                    "project_type",
                ),
        },
    }


def get_supabase_projects() -> list[dict[str, Any]]:
    """
    Return all projects from Supabase in the legacy shape expected by
    aios.projects.
    """
    repository = ProjectRepository(
        SupabaseStore()
    )

    projects = (
        repository.get_all_projects()
    )

    payloads = [
        project_to_legacy_payload(
            project
        )
        for project in projects
    ]

    print(
        "[Project Source] "
        f"Loaded projects from Supabase: "
        f"{len(payloads)}"
    )

    return payloads


def normalize_status(
    value: Optional[str],
) -> str:
    return " ".join(
        str(value or "")
        .strip()
        .lower()
        .split()
    )


def legacy_status(
    project: dict[str, Any],
) -> Optional[str]:
    prop = (
        project
        .get("properties", {})
        .get("Status", {})
    )

    select = prop.get(
        "select"
    )

    if isinstance(
        select,
        dict,
    ):
        return select.get(
            "name"
        )

    status = prop.get(
        "status"
    )

    if isinstance(
        status,
        dict,
    ):
        return status.get(
            "name"
        )

    return None


def legacy_active_checkbox(
    project: dict[str, Any],
) -> Optional[bool]:
    prop = (
        project
        .get("properties", {})
        .get("Active", {})
    )

    if prop.get(
        "type"
    ) == "checkbox":
        return bool(
            prop.get(
                "checkbox"
            )
        )

    return None


def is_active_legacy_project(
    project: dict[str, Any],
) -> bool:
    """
    Mirror the current aios.projects active-project rules so validation can
    compare read paths independently.
    """
    status = normalize_status(
        legacy_status(
            project
        )
    )

    if status in INACTIVE_PROJECT_STATUS_VALUES:
        return False

    if status in ACTIVE_PROJECT_STATUS_VALUES:
        return True

    active = legacy_active_checkbox(
        project
    )

    if active is True:
        return True

    if not status:
        return active is not False

    return False
