from __future__ import annotations

from typing import Optional

from aios.storage.project_repository import ProjectRepository
from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_repository import TaskRepository


class SupabaseProjectRelationWriter:
    """
    Supabase-only task -> project relation writer.

    Task references currently arrive primarily as legacy Notion task IDs.

    Project references can now be either:
      - a migrated project's legacy Notion ID, or
      - a native Supabase project UUID for projects created after the
        Supabase-only project-creation cutover.
    """

    def __init__(self):
        self.store = SupabaseStore()
        self.task_repository = TaskRepository(self.store)
        self.project_repository = ProjectRepository(self.store)

        self._task_map: dict[str, str] | None = None
        self._project_legacy_map: dict[str, str] | None = None
        self._project_ids: set[str] | None = None

    def _ensure_maps(self) -> None:
        if self._task_map is None:
            tasks = self.task_repository.get_all_tasks()

            self._task_map = {
                task.legacy_notion_id: task.id
                for task in tasks
                if task.legacy_notion_id
            }

            print(
                "[Project Relation Write] "
                f"Loaded task ID mappings: {len(self._task_map)}"
            )

        if (
            self._project_legacy_map is None
            or self._project_ids is None
        ):
            projects = (
                self.project_repository.get_all_projects()
            )

            self._project_legacy_map = {
                project.legacy_notion_id: project.id
                for project in projects
                if project.legacy_notion_id
            }

            self._project_ids = {
                project.id
                for project in projects
            }

            print(
                "[Project Relation Write] "
                f"Loaded projects: {len(self._project_ids)} "
                f"({len(self._project_legacy_map)} legacy mappings)"
            )

    def refresh_projects(self) -> None:
        """
        Refresh project identities after a project is created during the same
        AIOS process.
        """
        self._project_legacy_map = None
        self._project_ids = None
        self._ensure_maps()

    def resolve_task_id(
        self,
        task_ref_id: str,
    ) -> str:
        self._ensure_maps()
        assert self._task_map is not None

        # Future-safe: allow a native Supabase task UUID if it is already
        # supplied by a migrated caller.
        direct = (
            self.store.client
            .table("tasks")
            .select("id")
            .eq("id", task_ref_id)
            .limit(1)
            .execute()
        )

        if direct.data:
            return task_ref_id

        task_id = self._task_map.get(
            task_ref_id
        )

        if not task_id:
            raise RuntimeError(
                "Could not resolve task reference "
                f"{task_ref_id} to Supabase."
            )

        return task_id

    def resolve_project_id(
        self,
        project_ref_id: str,
    ) -> str:
        self._ensure_maps()

        assert self._project_legacy_map is not None
        assert self._project_ids is not None

        # New Supabase-only projects use their native UUID in the legacy-shaped
        # compatibility object returned to aios.projects.
        if project_ref_id in self._project_ids:
            return project_ref_id

        project_id = self._project_legacy_map.get(
            project_ref_id
        )

        if not project_id:
            # Project may have been created after this writer cached its maps.
            self.refresh_projects()

            assert self._project_legacy_map is not None
            assert self._project_ids is not None

            if project_ref_id in self._project_ids:
                return project_ref_id

            project_id = self._project_legacy_map.get(
                project_ref_id
            )

        if not project_id:
            raise RuntimeError(
                "Could not resolve project reference "
                f"{project_ref_id} to Supabase."
            )

        return project_id

    def write_supabase(
        self,
        *,
        notion_task_id: str,
        notion_project_id: Optional[str],
    ) -> tuple[str, Optional[str]]:
        """
        Keep the historical parameter names for call-site compatibility.
        Values may now be either legacy IDs or native Supabase IDs.
        """
        task_id = self.resolve_task_id(
            notion_task_id
        )

        project_id = (
            self.resolve_project_id(
                notion_project_id
            )
            if notion_project_id
            else None
        )

        response = (
            self.store.client
            .table("tasks")
            .update({
                "project_id": project_id,
            })
            .eq("id", task_id)
            .execute()
        )

        if not (response.data or []):
            raise RuntimeError(
                "Supabase project relation write returned no row."
            )

        return task_id, project_id


_WRITER: SupabaseProjectRelationWriter | None = None


def get_project_relation_writer() -> SupabaseProjectRelationWriter:
    global _WRITER

    if _WRITER is None:
        _WRITER = SupabaseProjectRelationWriter()

    return _WRITER
