from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from aios.storage.project_repository import ProjectRepository
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


def project_to_legacy_payload(
    project,
) -> dict[str, Any]:
    """
    Return the legacy-shaped project object still expected by the
    transitional aios.projects runtime.
    """
    return {
        "id": (
            project.legacy_notion_id
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
        },
    }


class SupabaseProjectLifecycleWriter:
    """
    Update lifecycle state for an EXISTING Supabase project.

    A project reference may be:
      - the native Supabase project UUID, or
      - a migrated project's legacy Notion page ID.

    Supported lifecycle fields:
      - status
      - is_active

    "Archive" remains a status/deactivation concept in the current AIOS
    project model; this writer does not physically delete project rows.
    """

    def __init__(self):
        self.store = SupabaseStore()
        self.repository = ProjectRepository(
            self.store
        )

        self._native_ids: set[str] | None = None
        self._legacy_to_native: dict[
            str,
            str,
        ] | None = None

    def _ensure_maps(self) -> None:
        if (
            self._native_ids is not None
            and self._legacy_to_native is not None
        ):
            return

        projects = (
            self.repository.get_all_projects()
        )

        self._native_ids = {
            project.id
            for project in projects
        }

        self._legacy_to_native = {
            project.legacy_notion_id:
                project.id
            for project in projects
            if project.legacy_notion_id
        }

    def refresh(self) -> None:
        self._native_ids = None
        self._legacy_to_native = None
        self._ensure_maps()

    def resolve_project_id(
        self,
        project_ref_id: str,
    ) -> str:
        self._ensure_maps()

        assert self._native_ids is not None
        assert self._legacy_to_native is not None

        if project_ref_id in self._native_ids:
            return project_ref_id

        project_id = (
            self._legacy_to_native.get(
                project_ref_id
            )
        )

        if not project_id:
            self.refresh()

            assert self._native_ids is not None
            assert self._legacy_to_native is not None

            if project_ref_id in self._native_ids:
                return project_ref_id

            project_id = (
                self._legacy_to_native.get(
                    project_ref_id
                )
            )

        if not project_id:
            raise RuntimeError(
                "Could not resolve project reference "
                f"{project_ref_id} to Supabase."
            )

        return project_id

    def update(
        self,
        *,
        project_ref_id: str,
        status: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> dict[str, Any]:
        """
        Update one or both lifecycle values.

        Passing None means "leave that field unchanged".
        """

        project_id = self.resolve_project_id(
            project_ref_id
        )

        current = self.repository.get_project(
            project_id
        )

        if current is None:
            raise RuntimeError(
                f"Supabase project {project_id} not found."
            )

        values: dict[str, Any] = {}

        if status is not None:
            values["status"] = str(
                status
            ).strip() or None

        if is_active is not None:
            values["is_active"] = bool(
                is_active
            )

        if not values:
            return project_to_legacy_payload(
                current
            )

        # projects may or may not expose updated_at through the repository
        # model, but the migrated schema includes normal timestamp support.
        values["updated_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        response = (
            self.store.client
            .table("projects")
            .update(values)
            .eq("id", project_id)
            .execute()
        )

        if not (response.data or []):
            raise RuntimeError(
                "Supabase project lifecycle write "
                "returned no row."
            )

        refreshed = self.repository.get_project(
            project_id
        )

        if refreshed is None:
            raise RuntimeError(
                "Project disappeared after "
                "lifecycle update."
            )

        print(
            "[Project Lifecycle Write] "
            f"Updated project {refreshed.name!r}: "
            f"status={refreshed.status!r}, "
            f"active={bool(refreshed.is_active)}"
        )

        return project_to_legacy_payload(
            refreshed
        )


_WRITER: SupabaseProjectLifecycleWriter | None = None


def get_project_lifecycle_writer() -> SupabaseProjectLifecycleWriter:
    global _WRITER

    if _WRITER is None:
        _WRITER = (
            SupabaseProjectLifecycleWriter()
        )

    return _WRITER
