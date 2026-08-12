"""
AIOS full Notion -> Supabase migration.

This script migrates the complete Tasks and Projects datasets from Notion
into Supabase using the repository layer.

DEFAULT BEHAVIOUR IS READ-ONLY.

Dry run:
    python -m scripts.supabase_full_import

Full write:
    python -m scripts.supabase_full_import --write

Reconciliation only:
    python -m scripts.supabase_full_import --reconcile-only

The migration:

1. Reads all Notion Projects and Tasks.
2. Converts them to datastore-neutral Project / Task models.
3. Upserts all Projects.
4. Builds Notion Project ID -> Supabase Project UUID mapping.
5. Upserts all Tasks with Project relationships, but no parent relationships.
6. Builds Notion Task ID -> Supabase Task UUID mapping.
7. Restores Parent Task relationships in a second pass.
8. Performs count and relationship reconciliation.

The script NEVER modifies Notion.
"""

from __future__ import annotations

import argparse
from dataclasses import replace

from aios.models import Project, Task
from aios.storage.project_repository import ProjectRepository
from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_repository import TaskRepository

from scripts.supabase_poc_import import (
    PROJECTS_DATABASE_ID,
    TASKS_DATABASE_ID,
    notion_project_to_model,
    notion_task_to_model,
    query_database,
)


# ---------------------------------------------------------------------------
# Source loading
# ---------------------------------------------------------------------------

def load_notion_data() -> tuple[
    list[Project],
    list[Task],
]:
    print("\nReading Projects from Notion...")

    project_pages = query_database(
        PROJECTS_DATABASE_ID
    )

    projects = [
        notion_project_to_model(page)
        for page in project_pages
    ]

    print(
        f"Projects read: {len(projects)}"
    )

    print("\nReading Tasks from Notion...")

    task_pages = query_database(
        TASKS_DATABASE_ID
    )

    tasks = [
        notion_task_to_model(page)
        for page in task_pages
    ]

    print(
        f"Tasks read: {len(tasks)}"
    )

    return projects, tasks


# ---------------------------------------------------------------------------
# Source statistics
# ---------------------------------------------------------------------------

def source_statistics(
    projects: list[Project],
    tasks: list[Task],
) -> dict[str, int]:

    open_tasks = sum(
        1
        for task in tasks
        if (
            task.is_open
            and not task.is_done
            and not task.is_archived
        )
    )

    project_links = sum(
        1
        for task in tasks
        if task.project_id
    )

    parent_links = sum(
        1
        for task in tasks
        if task.parent_task_id
    )

    suggested_projects = sum(
        1
        for task in tasks
        if task.suggested_project
    )

    metadata_tasks = sum(
        1
        for task in tasks
        if task.legacy_metadata
    )

    metadata_projects = sum(
        1
        for project in projects
        if project.legacy_metadata
    )

    return {
        "projects": len(projects),
        "tasks": len(tasks),
        "open_tasks": open_tasks,
        "project_links": project_links,
        "parent_links": parent_links,
        "suggested_projects": suggested_projects,
        "metadata_tasks": metadata_tasks,
        "metadata_projects": metadata_projects,
    }


def print_source_statistics(
    stats: dict[str, int],
) -> None:

    print("\n" + "=" * 72)
    print("SOURCE MIGRATION SUMMARY")
    print("=" * 72)

    print(
        f"Projects:                  "
        f"{stats['projects']}"
    )

    print(
        f"Tasks:                     "
        f"{stats['tasks']}"
    )

    print(
        f"Open tasks:                "
        f"{stats['open_tasks']}"
    )

    print(
        f"Task -> Project links:     "
        f"{stats['project_links']}"
    )

    print(
        f"Parent Task links:         "
        f"{stats['parent_links']}"
    )

    print(
        f"Suggested Project values:  "
        f"{stats['suggested_projects']}"
    )

    print(
        f"Tasks with legacy data:    "
        f"{stats['metadata_tasks']}"
    )

    print(
        f"Projects with legacy data: "
        f"{stats['metadata_projects']}"
    )


# ---------------------------------------------------------------------------
# Project migration
# ---------------------------------------------------------------------------

def migrate_projects(
    repository: ProjectRepository,
    projects: list[Project],
) -> dict[str, str]:

    print("\n" + "=" * 72)
    print("MIGRATING PROJECTS")
    print("=" * 72)

    project_map: dict[str, str] = {}

    total = len(projects)

    for index, project in enumerate(
        projects,
        start=1,
    ):

        stored = repository.upsert_project(
            project
        )

        if project.legacy_notion_id:
            project_map[
                project.legacy_notion_id
            ] = stored.id

        if (
            index == 1
            or index % 10 == 0
            or index == total
        ):
            print(
                f"Projects migrated: "
                f"{index}/{total}"
            )

    print(
        f"Project ID mappings: "
        f"{len(project_map)}"
    )

    return project_map


# ---------------------------------------------------------------------------
# Task migration — first pass
# ---------------------------------------------------------------------------

def migrate_tasks_first_pass(
    repository: TaskRepository,
    tasks: list[Task],
    project_map: dict[str, str],
) -> dict[str, str]:

    print("\n" + "=" * 72)
    print("MIGRATING TASKS — FIRST PASS")
    print("=" * 72)

    print(
        "Project relationships will be applied now."
    )

    print(
        "Parent relationships will be applied "
        "in the second pass."
    )

    task_map: dict[str, str] = {}

    missing_project_mappings = 0

    total = len(tasks)

    for index, task in enumerate(
        tasks,
        start=1,
    ):

        supabase_project_id = None

        if task.project_id:

            supabase_project_id = (
                project_map.get(
                    task.project_id
                )
            )

            if not supabase_project_id:
                missing_project_mappings += 1

                print(
                    "\nWARNING: No Supabase "
                    "project mapping for:"
                )

                print(
                    f"  {task.title}"
                )

        migration_task = replace(
            task,
            project_id=supabase_project_id,
            parent_task_id=None,
        )

        stored = repository.upsert_task(
            migration_task
        )

        if task.legacy_notion_id:
            task_map[
                task.legacy_notion_id
            ] = stored.id

        if (
            index == 1
            or index % 100 == 0
            or index == total
        ):
            print(
                f"Tasks migrated: "
                f"{index}/{total}"
            )

    print(
        f"\nTask ID mappings: "
        f"{len(task_map)}"
    )

    print(
        f"Missing project mappings: "
        f"{missing_project_mappings}"
    )

    if missing_project_mappings:
        raise RuntimeError(
            "One or more Project relationships "
            "could not be mapped."
        )

    return task_map


# ---------------------------------------------------------------------------
# Task migration — parent second pass
# ---------------------------------------------------------------------------

def migrate_parent_relationships(
    repository: TaskRepository,
    tasks: list[Task],
    task_map: dict[str, str],
) -> int:

    print("\n" + "=" * 72)
    print("MIGRATING PARENT TASK RELATIONSHIPS")
    print("=" * 72)

    tasks_with_parent = [
        task
        for task in tasks
        if task.parent_task_id
    ]

    total = len(tasks_with_parent)

    updated = 0
    missing = 0

    for task in tasks_with_parent:

        if not task.legacy_notion_id:
            missing += 1
            continue

        child_supabase_id = (
            task_map.get(
                task.legacy_notion_id
            )
        )

        parent_supabase_id = (
            task_map.get(
                task.parent_task_id
            )
        )

        if (
            not child_supabase_id
            or not parent_supabase_id
        ):
            missing += 1

            print(
                "\nWARNING: Unable to map "
                "parent relationship:"
            )

            print(
                f"  Child:  {task.title}"
            )

            print(
                f"  Parent Notion ID: "
                f"{task.parent_task_id}"
            )

            continue

        repository.update_parent_task(
            child_supabase_id,
            parent_supabase_id,
        )

        updated += 1

        if (
            updated == 1
            or updated % 50 == 0
            or updated == total
        ):
            print(
                f"Parent links migrated: "
                f"{updated}/{total}"
            )

    print(
        f"\nParent relationships applied: "
        f"{updated}"
    )

    print(
        f"Parent relationships missing: "
        f"{missing}"
    )

    if missing:
        raise RuntimeError(
            "One or more Parent Task "
            "relationships could not be mapped."
        )

    return updated


# ---------------------------------------------------------------------------
# Supabase reconciliation
# ---------------------------------------------------------------------------

def reconcile(
    project_repository: ProjectRepository,
    task_repository: TaskRepository,
    source_stats: dict[str, int],
) -> None:

    print("\n" + "=" * 72)
    print("FULL MIGRATION RECONCILIATION")
    print("=" * 72)

    projects = (
        project_repository
        .get_all_projects()
    )

    # TaskRepository now paginates, so this returns
    # the complete dataset rather than stopping at 1,000.
    tasks = (
        task_repository
        .get_all_tasks()
    )

    open_tasks = [
        task
        for task in tasks
        if (
            task.is_open
            and not task.is_done
            and not task.is_archived
        )
    ]

    project_links = [
        task
        for task in tasks
        if task.project_id
    ]

    parent_links = [
        task
        for task in tasks
        if task.parent_task_id
    ]

    suggested_projects = [
        task
        for task in tasks
        if task.suggested_project
    ]

    metadata_tasks = [
        task
        for task in tasks
        if task.legacy_metadata
    ]

    metadata_projects = [
        project
        for project in projects
        if project.legacy_metadata
    ]

    checks = [
        (
            "Projects",
            source_stats["projects"],
            len(projects),
        ),
        (
            "Tasks",
            source_stats["tasks"],
            len(tasks),
        ),
        (
            "Open tasks",
            source_stats["open_tasks"],
            len(open_tasks),
        ),
        (
            "Project links",
            source_stats["project_links"],
            len(project_links),
        ),
        (
            "Parent links",
            source_stats["parent_links"],
            len(parent_links),
        ),
        (
            "Suggested projects",
            source_stats["suggested_projects"],
            len(suggested_projects),
        ),
        (
            "Tasks with legacy metadata",
            source_stats["metadata_tasks"],
            len(metadata_tasks),
        ),
        (
            "Projects with legacy metadata",
            source_stats["metadata_projects"],
            len(metadata_projects),
        ),
    ]

    failures = []

    for (
        label,
        expected,
        actual,
    ) in checks:

        result = (
            "MATCH"
            if expected == actual
            else "DIFF"
        )

        print(
            f"{result:5} "
            f"{label:<30} "
            f"Notion={expected:<5} "
            f"Supabase={actual:<5}"
        )

        if expected != actual:
            failures.append(
                (
                    label,
                    expected,
                    actual,
                )
            )

    if failures:

        print(
            "\nRESULT: MIGRATION "
            "RECONCILIATION FAILED"
        )

        print(
            "\nDifferences:"
        )

        for (
            label,
            expected,
            actual,
        ) in failures:

            print(
                f"  - {label}: "
                f"expected {expected}, "
                f"found {actual}"
            )

        raise RuntimeError(
            "Full migration reconciliation failed."
        )

    print(
        "\nRESULT: EXACT DATASET RECONCILIATION"
    )


# ---------------------------------------------------------------------------
# Arguments
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description=(
            "Full AIOS Notion -> Supabase migration"
        )
    )

    parser.add_argument(
        "--write",
        action="store_true",
        help=(
            "Perform the full Supabase migration. "
            "Without this flag the command is read-only."
        ),
    )

    parser.add_argument(
        "--reconcile-only",
        action="store_true",
        help=(
            "Skip migration writes and only compare "
            "the current Supabase dataset to Notion."
        ),
    )

    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:

    args = parse_args()

    if (
        args.write
        and args.reconcile_only
    ):
        raise ValueError(
            "Choose either --write or --reconcile-only, "
            "not both."
        )

    print("=" * 72)
    print("AIOS FULL SUPABASE MIGRATION")
    print("=" * 72)

    if args.reconcile_only:

        print(
            "MODE: RECONCILIATION ONLY"
        )

    elif args.write:

        print(
            "MODE: FULL WRITE TO SUPABASE"
        )

    else:

        print(
            "MODE: DRY RUN — "
            "NO SUPABASE WRITES"
        )

    print(
        "Notion remains read-only."
    )

    projects, tasks = (
        load_notion_data()
    )

    stats = source_statistics(
        projects,
        tasks,
    )

    print_source_statistics(
        stats
    )

    # Plain dry run.
    if (
        not args.write
        and not args.reconcile_only
    ):

        print(
            "\nDRY RUN COMPLETE."
        )

        print(
            "\nNo Supabase records were changed."
        )

        print(
            "\nTo perform the migration:"
        )

        print(
            "  python -m "
            "scripts.supabase_full_import "
            "--write"
        )

        print(
            "\nTo validate the current "
            "Supabase dataset only:"
        )

        print(
            "  python -m "
            "scripts.supabase_full_import "
            "--reconcile-only"
        )

        return

    print("\nConnecting to Supabase...")

    store = SupabaseStore()

    project_repository = (
        ProjectRepository(store)
    )

    task_repository = (
        TaskRepository(store)
    )

    print(
        "Supabase connection successful."
    )

    # Reconciliation-only mode.
    if args.reconcile_only:

        reconcile(
            project_repository,
            task_repository,
            stats,
        )

        print("\n" + "=" * 72)
        print("RECONCILIATION COMPLETED")
        print("=" * 72)

        print(
            "\nNo Supabase records were changed."
        )

        return

    # Full-write mode.
    project_map = migrate_projects(
        project_repository,
        projects,
    )

    task_map = migrate_tasks_first_pass(
        task_repository,
        tasks,
        project_map,
    )

    migrate_parent_relationships(
        task_repository,
        tasks,
        task_map,
    )

    reconcile(
        project_repository,
        task_repository,
        stats,
    )

    print("\n" + "=" * 72)
    print("FULL SUPABASE MIGRATION COMPLETED")
    print("=" * 72)

    print(
        "\nNotion was not modified."
    )

    print(
        "Supabase now contains the "
        "full migrated dataset."
    )


if __name__ == "__main__":
    main()