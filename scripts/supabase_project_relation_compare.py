"""
Compare current Notion task -> project relations to Supabase.

READ ONLY.

During this temporary mirror stage, every Notion task relation should map to
the same Supabase tasks.project_id relation.

Run:
    python -m scripts.supabase_project_relation_compare
"""

from __future__ import annotations

from aios.storage.project_repository import ProjectRepository
from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_repository import TaskRepository

from scripts.supabase_poc_import import (
    TASKS_DATABASE_ID,
    query_database,
)


def notion_relation_ids(
    props,
    name,
):
    prop = props.get(
        name,
        {},
    )

    values = prop.get(
        "relation",
        [],
    )

    return [
        item.get("id")
        for item in values
        if item.get("id")
    ]


def main() -> None:
    print("=" * 72)
    print(
        "AIOS TASK / PROJECT RELATION "
        "NOTION-SUPABASE COMPARISON"
    )
    print("=" * 72)
    print("\nREAD ONLY.")

    store = SupabaseStore()

    task_repo = TaskRepository(
        store
    )
    project_repo = ProjectRepository(
        store
    )

    tasks = task_repo.get_all_tasks()
    projects = (
        project_repo.get_all_projects()
    )

    notion_task_to_supabase = {
        task.legacy_notion_id: task
        for task in tasks
        if task.legacy_notion_id
    }

    notion_project_to_supabase = {
        project.legacy_notion_id: project.id
        for project in projects
        if project.legacy_notion_id
    }

    pages = query_database(
        TASKS_DATABASE_ID
    )

    expected = {}
    multi_project = []
    missing_task_map = []
    missing_project_map = []

    for page in pages:
        notion_task_id = page.get(
            "id"
        )

        relations = notion_relation_ids(
            page.get(
                "properties",
                {},
            ),
            "Project",
        )

        if len(relations) > 1:
            multi_project.append(
                notion_task_id
            )
            continue

        task = notion_task_to_supabase.get(
            notion_task_id
        )

        if task is None:
            missing_task_map.append(
                notion_task_id
            )
            continue

        expected_project_id = None

        if relations:
            expected_project_id = (
                notion_project_to_supabase.get(
                    relations[0]
                )
            )

            if not expected_project_id:
                missing_project_map.append(
                    relations[0]
                )
                continue

        expected[task.id] = (
            expected_project_id
        )

    differences = []

    for task in tasks:
        if task.id not in expected:
            continue

        if (
            task.project_id
            != expected[task.id]
        ):
            differences.append(
                task.id
            )

    notion_link_count = sum(
        1
        for value in expected.values()
        if value
    )

    supabase_link_count = sum(
        1
        for task in tasks
        if task.project_id
    )

    print(
        f"\nNotion task pages:          "
        f"{len(pages)}"
    )
    print(
        f"Supabase tasks:             "
        f"{len(tasks)}"
    )
    print(
        f"Notion project links:       "
        f"{notion_link_count}"
    )
    print(
        f"Supabase project links:     "
        f"{supabase_link_count}"
    )
    print(
        f"Multi-project Notion tasks: "
        f"{len(multi_project)}"
    )
    print(
        f"Missing task mappings:      "
        f"{len(missing_task_map)}"
    )
    print(
        f"Missing project mappings:   "
        f"{len(missing_project_map)}"
    )
    print(
        f"Different relations:        "
        f"{len(differences)}"
    )

    failures = []

    if multi_project:
        failures.append(
            "Notion contains multi-project task relations."
        )

    if missing_task_map:
        failures.append(
            f"Missing task mappings: "
            f"{len(missing_task_map)}"
        )

    if missing_project_map:
        failures.append(
            f"Missing project mappings: "
            f"{len(missing_project_map)}"
        )

    if notion_link_count != supabase_link_count:
        failures.append(
            "Project relation counts differ: "
            f"Notion={notion_link_count}, "
            f"Supabase={supabase_link_count}"
        )

    if differences:
        failures.append(
            f"Different task/project relations: "
            f"{len(differences)}"
        )

    if failures:
        print(
            "\nRESULT: PROJECT RELATION "
            "PARITY FAILED"
        )

        for failure in failures:
            print(
                f"  - {failure}"
            )

        raise SystemExit(1)

    print(
        "\nRESULT: EXACT TASK / PROJECT "
        "RELATION PARITY"
    )


if __name__ == "__main__":
    main()
