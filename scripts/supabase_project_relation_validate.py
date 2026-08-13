"""
Read-only validation for Supabase task -> project relations.

Notion parity is intentionally NOT checked after the Supabase-only cutover.

Run:
    python -m scripts.supabase_project_relation_validate
"""

from __future__ import annotations

from aios.storage.project_repository import ProjectRepository
from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_repository import TaskRepository


BASELINE_PROJECT_LINKS = 307


def main() -> None:
    print("=" * 72)
    print("AIOS SUPABASE PROJECT RELATION VALIDATION")
    print("=" * 72)
    print("\nREAD ONLY.")

    store = SupabaseStore()
    task_repo = TaskRepository(store)
    project_repo = ProjectRepository(store)

    tasks = task_repo.get_all_tasks()
    projects = project_repo.get_all_projects()

    project_ids = {
        project.id
        for project in projects
    }

    linked_tasks = [
        task
        for task in tasks
        if task.project_id
    ]

    orphaned = [
        task
        for task in linked_tasks
        if task.project_id not in project_ids
    ]

    invalid_self_parent = [
        task
        for task in tasks
        if (
            task.parent_task_id
            and task.parent_task_id == task.id
        )
    ]

    print(f"\nTotal tasks:              {len(tasks)}")
    print(f"Total projects:           {len(projects)}")
    print(f"Tasks with project link:  {len(linked_tasks)}")
    print(f"Orphaned project links:   {len(orphaned)}")
    print(f"Self-parent task links:   {len(invalid_self_parent)}")
    print(
        f"Baseline project links:   {BASELINE_PROJECT_LINKS}"
    )

    failures = []

    if orphaned:
        failures.append(
            f"Orphaned project links: {len(orphaned)}"
        )

    if invalid_self_parent:
        failures.append(
            f"Self-parent task links: {len(invalid_self_parent)}"
        )

    if len(linked_tasks) < BASELINE_PROJECT_LINKS:
        failures.append(
            "Project-link count dropped below verified baseline: "
            f"baseline={BASELINE_PROJECT_LINKS}, "
            f"current={len(linked_tasks)}"
        )

    if failures:
        print(
            "\nRESULT: SUPABASE PROJECT RELATION "
            "VALIDATION FAILED"
        )

        for failure in failures:
            print(f"  - {failure}")

        raise SystemExit(1)

    if len(linked_tasks) > BASELINE_PROJECT_LINKS:
        print(
            "\nNote: project-link count is above the migration "
            "baseline, consistent with new valid relations."
        )

    print(
        "\nRESULT: SUPABASE PROJECT RELATIONS ARE CLEAN"
    )


if __name__ == "__main__":
    main()
