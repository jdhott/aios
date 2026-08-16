from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from aios.models import Project
from aios.storage.supabase_store import SupabaseStore


def parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None

    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


class ProjectRepository:
    """
    Supabase persistence layer for AIOS projects.

    Converts Supabase rows into datastore-neutral Project models.
    """

    def __init__(self, store: SupabaseStore):
        self.store = store

    def row_to_project(
        self,
        row: dict[str, Any],
    ) -> Project:
        return Project(
            id=row["id"],
            legacy_notion_id=row.get("legacy_notion_id"),
            name=row.get("name") or "(Untitled Project)",
            status=row.get("status"),
            is_active=row.get("is_active", False),
            outcome=row.get("outcome"),
            context=row.get("context"),
            possible_existing_project_id=row.get(
                "possible_existing_project_id"
            ),
            possible_existing_project_confidence=row.get(
                "possible_existing_project_confidence"
            ),
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

    def get_all_projects(self) -> list[Project]:
        response = (
            self.store.client
            .table("projects")
            .select("*")
            .order("created_at")
            .execute()
        )

        return [
            self.row_to_project(row)
            for row in (response.data or [])
        ]

    def get_active_projects(self) -> list[Project]:
        response = (
            self.store.client
            .table("projects")
            .select("*")
            .eq("is_active", True)
            .order("name")
            .execute()
        )

        return [
            self.row_to_project(row)
            for row in (response.data or [])
        ]

    def get_project(
        self,
        project_id: str,
    ) -> Optional[Project]:
        response = (
            self.store.client
            .table("projects")
            .select("*")
            .eq("id", project_id)
            .limit(1)
            .execute()
        )

        rows = response.data or []

        if not rows:
            return None

        return self.row_to_project(rows[0])

    def get_project_by_legacy_notion_id(
        self,
        notion_id: str,
    ) -> Optional[Project]:
        response = (
            self.store.client
            .table("projects")
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

        return self.row_to_project(rows[0])

    def count_projects(self) -> int:
        response = (
            self.store.client
            .table("projects")
            .select(
                "id",
                count="exact",
            )
            .execute()
        )

        return response.count or 0

    def upsert_project(
        self,
        project: Project,
    ) -> Project:
        payload = {
            "legacy_notion_id": project.legacy_notion_id,
            "name": project.name,
            "status": project.status,
            "is_active": project.is_active,
            "outcome": project.outcome,
            "context": project.context,
            "legacy_metadata": project.legacy_metadata,
            "created_at": (
                project.created_at.isoformat()
                if project.created_at
                else None
            ),
            "updated_at": (
                project.updated_at.isoformat()
                if project.updated_at
                else None
            ),
            "completed_at": (
                project.completed_at.isoformat()
                if project.completed_at
                else None
            ),
        }

        response = (
            self.store.client
            .table("projects")
            .upsert(
                payload,
                on_conflict="legacy_notion_id",
            )
            .execute()
        )

        if not response.data:
            raise RuntimeError(
                f"Failed to upsert project: {project.name}"
            )

        return self.row_to_project(
            response.data[0]
        )

    def upsert_projects(
        self,
        projects: list[Project],
    ) -> list[Project]:
        return [
            self.upsert_project(project)
            for project in projects
        ]