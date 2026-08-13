"""
Read-only validation after Supabase-only project creation cutover.

Notion parity is intentionally NOT required.

This validator preserves verified legacy conditions while still protecting
against new structural problems.

Verified legacy condition:
- Two projects named "Home Networking and Infrastructure" already existed:
    - one archived/inactive
    - one active
  This duplicate normalized name is allowed as a legacy baseline.

Run:
    python -m scripts.supabase_project_structure_validate
"""

from __future__ import annotations

from collections import Counter

from aios.storage.project_repository import ProjectRepository
from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_repository import TaskRepository


MIGRATED_PROJECT_BASELINE = 36

LEGACY_DUPLICATE_PROJECT_NAME_BASELINE = {
    "home networking and infrastructure": 2,
}


def normalize_name(
    value: str,
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
        "STRUCTURE VALIDATION"
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

    empty_names = [
        project.id
        for project in projects
        if not str(
            project.name or ""
        ).strip()
    ]

    migrated_projects = [
        project
        for project in projects
        if project.legacy_notion_id
    ]

    native_projects = [
        project
        for project in projects
        if not project.legacy_notion_id
    ]

    normalized_names = [
        normalize_name(
            project.name
        )
        for project in projects
        if normalize_name(
            project.name
        )
    ]

    duplicate_name_counts = {
        name: count
        for name, count
        in Counter(
            normalized_names
        ).items()
        if count > 1
    }

    unexpected_duplicates = {}

    for (
        name,
        count,
    ) in duplicate_name_counts.items():

        allowed_count = (
            LEGACY_DUPLICATE_PROJECT_NAME_BASELINE
            .get(
                name,
                1,
            )
        )

        if count > allowed_count:
            unexpected_duplicates[
                name
            ] = {
                "count":
                    count,

                "allowed":
                    allowed_count,
            }

    # Also ensure none of the allowed legacy duplicate groups has somehow
    # grown through newly-created Supabase-native projects.
    native_duplicate_conflicts = []

    for project in native_projects:

        normalized = normalize_name(
            project.name
        )

        if (
            normalized
            in
            LEGACY_DUPLICATE_PROJECT_NAME_BASELINE
        ):
            native_duplicate_conflicts.append(
                project.id
            )

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

    print(
        f"\nProjects:                    "
        f"{len(projects)}"
    )

    print(
        f"Migrated projects:           "
        f"{len(migrated_projects)}"
    )

    print(
        f"Supabase-native projects:    "
        f"{len(native_projects)}"
    )

    print(
        f"Projects with empty names:   "
        f"{len(empty_names)}"
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
        f"Native legacy-name conflicts:"
        f" {len(native_duplicate_conflicts)}"
    )

    print(
        f"Task/project links:          "
        f"{len(linked_tasks)}"
    )

    print(
        f"Orphaned project links:      "
        f"{len(orphaned_links)}"
    )

    if duplicate_name_counts:

        print(
            "\nDuplicate normalized "
            "project-name groups:"
        )

        for (
            name,
            count,
        ) in sorted(
            duplicate_name_counts.items()
        ):

            allowed = (
                LEGACY_DUPLICATE_PROJECT_NAME_BASELINE
                .get(
                    name
                )
            )

            if allowed is not None:
                print(
                    f"  - {name!r}: "
                    f"{count} "
                    f"(legacy baseline allows "
                    f"{allowed})"
                )

            else:
                print(
                    f"  - {name!r}: "
                    f"{count} "
                    "(no legacy duplicate allowed)"
                )

    failures = []

    if (
        len(projects)
        <
        MIGRATED_PROJECT_BASELINE
    ):
        failures.append(
            "Project count dropped below "
            "migration baseline: "
            f"{len(projects)} "
            f"< "
            f"{MIGRATED_PROJECT_BASELINE}"
        )

    if (
        len(migrated_projects)
        <
        MIGRATED_PROJECT_BASELINE
    ):
        failures.append(
            "Migrated project population "
            "dropped below baseline: "
            f"{len(migrated_projects)} "
            f"< "
            f"{MIGRATED_PROJECT_BASELINE}"
        )

    if empty_names:
        failures.append(
            "Projects with empty names: "
            f"{len(empty_names)}"
        )

    if unexpected_duplicates:
        failures.append(
            "Unexpected duplicate normalized "
            "project names: "
            f"{len(unexpected_duplicates)}"
        )

    if native_duplicate_conflicts:
        failures.append(
            "Supabase-native projects reused "
            "a verified legacy duplicate name: "
            f"{len(native_duplicate_conflicts)}"
        )

    if orphaned_links:
        failures.append(
            "Orphaned task/project links: "
            f"{len(orphaned_links)}"
        )

    if failures:

        print(
            "\nRESULT: SUPABASE PROJECT "
            "STRUCTURE VALIDATION FAILED"
        )

        for failure in failures:
            print(
                f"  - {failure}"
            )

        if unexpected_duplicates:

            print(
                "\nUnexpected duplicate details:"
            )

            for (
                name,
                info,
            ) in sorted(
                unexpected_duplicates.items()
            ):

                print(
                    f"  - {name!r}: "
                    f"count={info['count']} "
                    f"allowed={info['allowed']}"
                )

        raise SystemExit(1)

    print(
        "\nVerified legacy duplicate "
        "project-name baseline preserved."
    )

    print(
        "\nRESULT: SUPABASE PROJECT "
        "STRUCTURE IS CLEAN"
    )


if __name__ == "__main__":
    main()