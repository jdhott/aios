"""
Read-only validation of Supabase project lifecycle state.

Notion parity is intentionally not required.

Run:
    python -m scripts.supabase_project_lifecycle_validate
"""

from __future__ import annotations

from collections import Counter

from aios.storage.project_repository import ProjectRepository
from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_repository import TaskRepository


MIGRATED_PROJECT_BASELINE = 36
PROJECT_LINK_BASELINE = 307

LEGACY_DUPLICATE_PROJECT_NAME_BASELINE = {
    "home networking and infrastructure": 2,
}

INACTIVE_STATUS_VALUES = {
    "archive",
    "archived",
    "completed",
    "done",
    "paused",
    "someday",
}


def normalize(
    value,
) -> str:
    return " ".join(
        str(value or "")
        .strip()
        .casefold()
        .split()
    )


def main() -> None:
    print("=" * 72)
    print(
        "AIOS SUPABASE PROJECT "
        "LIFECYCLE VALIDATION"
    )
    print("=" * 72)
    print("\nREAD ONLY.")

    store = SupabaseStore()

    project_repo = ProjectRepository(
        store
    )

    task_repo = TaskRepository(
        store
    )

    projects = (
        project_repo.get_all_projects()
    )

    tasks = (
        task_repo.get_all_tasks()
    )

    project_ids = {
        project.id
        for project in projects
    }

    migrated = [
        project
        for project in projects
        if project.legacy_notion_id
    ]

    native = [
        project
        for project in projects
        if not project.legacy_notion_id
    ]

    empty_names = [
        project.id
        for project in projects
        if not normalize(
            project.name
        )
    ]

    active_with_inactive_status = [
        project
        for project in projects
        if (
            bool(
                project.is_active
            )
            and normalize(
                project.status
            )
            in INACTIVE_STATUS_VALUES
        )
    ]

    name_counts = Counter(
        normalize(
            project.name
        )
        for project in projects
        if normalize(
            project.name
        )
    )

    duplicate_name_counts = {
        name: count
        for name, count
        in name_counts.items()
        if count > 1
    }

    unexpected_duplicates = {
        name: count
        for name, count
        in duplicate_name_counts.items()
        if count
        >
        LEGACY_DUPLICATE_PROJECT_NAME_BASELINE.get(
            name,
            1,
        )
    }

    linked_tasks = [
        task
        for task in tasks
        if task.project_id
    ]

    orphaned_links = [
        task.id
        for task in linked_tasks
        if task.project_id not in project_ids
    ]

    status_counts = Counter(
        str(
            project.status
            if project.status is not None
            else "(unset)"
        )
        for project in projects
    )

    active_count = sum(
        1
        for project in projects
        if bool(
            project.is_active
        )
    )

    print(
        f"\nProjects:                    "
        f"{len(projects)}"
    )
    print(
        f"Migrated projects:           "
        f"{len(migrated)}"
    )
    print(
        f"Supabase-native projects:    "
        f"{len(native)}"
    )
    print(
        f"Active projects:             "
        f"{active_count}"
    )
    print(
        f"Projects with empty names:   "
        f"{len(empty_names)}"
    )
    print(
        "Active with inactive status: "
        f"{len(active_with_inactive_status)}"
    )
    print(
        f"Duplicate normalized names:  "
        f"{len(duplicate_name_counts)}"
    )
    print(
        f"Unexpected duplicates:       "
        f"{len(unexpected_duplicates)}"
    )
    print(
        f"Task/project links:          "
        f"{len(linked_tasks)}"
    )
    print(
        f"Orphaned project links:      "
        f"{len(orphaned_links)}"
    )

    print(
        "\nProject status distribution:"
    )

    for (
        status,
        count,
    ) in status_counts.most_common():
        print(
            f"  {status}: {count}"
        )

    failures = []

    if len(projects) < MIGRATED_PROJECT_BASELINE:
        failures.append(
            "Project count dropped below baseline: "
            f"{len(projects)} "
            f"< {MIGRATED_PROJECT_BASELINE}"
        )

    if len(migrated) < MIGRATED_PROJECT_BASELINE:
        failures.append(
            "Migrated project count dropped below baseline: "
            f"{len(migrated)} "
            f"< {MIGRATED_PROJECT_BASELINE}"
        )

    if empty_names:
        failures.append(
            f"Projects with empty names: "
            f"{len(empty_names)}"
        )

    if active_with_inactive_status:
        failures.append(
            "Active projects have inactive/archive statuses: "
            f"{len(active_with_inactive_status)}"
        )

    if unexpected_duplicates:
        failures.append(
            "Unexpected duplicate normalized project names: "
            f"{len(unexpected_duplicates)}"
        )

    if len(linked_tasks) < PROJECT_LINK_BASELINE:
        failures.append(
            "Project-link count dropped below baseline: "
            f"{len(linked_tasks)} "
            f"< {PROJECT_LINK_BASELINE}"
        )

    if orphaned_links:
        failures.append(
            f"Orphaned project links: "
            f"{len(orphaned_links)}"
        )

    if failures:
        print(
            "\nRESULT: SUPABASE PROJECT "
            "LIFECYCLE VALIDATION FAILED"
        )

        for failure in failures:
            print(
                f"  - {failure}"
            )

        raise SystemExit(1)

    print(
        "\nRESULT: SUPABASE PROJECT "
        "LIFECYCLE IS CLEAN"
    )


if __name__ == "__main__":
    main()
