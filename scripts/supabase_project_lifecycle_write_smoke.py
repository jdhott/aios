"""
Idempotent smoke test for Supabase project lifecycle writes.

Writes one project's existing status and active values back unchanged, then
verifies semantic state was preserved.

Run:
    python -m scripts.supabase_project_lifecycle_write_smoke
"""

from __future__ import annotations

from aios.storage.project_lifecycle_writer import (
    SupabaseProjectLifecycleWriter,
)
from aios.storage.project_repository import ProjectRepository
from aios.storage.supabase_store import SupabaseStore


def main() -> None:
    store = SupabaseStore()

    repo = ProjectRepository(
        store
    )

    projects = (
        repo.get_all_projects()
    )

    candidate = next(
        (
            project
            for project in projects
            if project.name
        ),
        None,
    )

    if candidate is None:
        raise RuntimeError(
            "No project available for smoke test."
        )

    before = {
        "status":
            candidate.status,
        "is_active":
            bool(
                candidate.is_active
            ),
    }

    writer = (
        SupabaseProjectLifecycleWriter()
    )

    writer.update(
        project_ref_id=candidate.id,
        status=candidate.status,
        is_active=bool(
            candidate.is_active
        ),
    )

    refreshed = repo.get_project(
        candidate.id
    )

    if refreshed is None:
        raise RuntimeError(
            "Project missing after smoke test."
        )

    after = {
        "status":
            refreshed.status,
        "is_active":
            bool(
                refreshed.is_active
            ),
    }

    if before != after:
        print(
            "Before:",
            before,
        )
        print(
            "After:",
            after,
        )

        raise RuntimeError(
            "Project lifecycle smoke test "
            "changed semantic state."
        )

    print(
        "Supabase project lifecycle write smoke test passed. "
        "Existing status/active state was preserved."
    )


if __name__ == "__main__":
    main()
