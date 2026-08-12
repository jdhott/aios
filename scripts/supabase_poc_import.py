"""
Supabase migration proof of concept.

Reads Projects and Tasks from the existing Notion databases and optionally
writes a controlled sample into Supabase through the repository layer.

DEFAULT BEHAVIOUR IS READ-ONLY.

Dry run:
    python -m scripts.supabase_poc_import

Controlled write:
    python -m scripts.supabase_poc_import --write

Change sample size:
    python -m scripts.supabase_poc_import --write --limit 25

This script does NOT modify Notion.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import replace
from datetime import datetime
from typing import Any, Callable, Optional

import requests
from dotenv import load_dotenv

from aios.models import Project, Task
from aios.storage.project_repository import ProjectRepository
from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_repository import TaskRepository


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv(override=True)

NOTION_TOKEN = os.environ["NOTION_TOKEN"]

TASKS_DATABASE_ID = (
    os.getenv("TASKS_DATABASE_ID")
    or os.getenv("NOTION_TASKS_DATABASE_ID")
    or ""
)

PROJECTS_DATABASE_ID = (
    os.getenv("PROJECTS_DATABASE_ID")
    or os.getenv("PROJECT_DATABASE_ID")
    or os.getenv("NOTION_PROJECTS_DATABASE_ID")
    or os.getenv("NOTION_PROJECT_DATABASE_ID")
    or ""
)

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


# ---------------------------------------------------------------------------
# Notion helpers
# ---------------------------------------------------------------------------

def query_database(
    database_id: str,
) -> list[dict[str, Any]]:
    """Read every record from a Notion database."""

    if not database_id:
        raise RuntimeError(
            "Notion database ID is not configured."
        )

    url = (
        f"https://api.notion.com/v1/databases/"
        f"{database_id}/query"
    )

    payload: dict[str, Any] = {
        "page_size": 100,
    }

    results: list[dict[str, Any]] = []

    while True:
        response = requests.post(
            url,
            headers=NOTION_HEADERS,
            json=payload,
            timeout=30,
        )

        if not response.ok:
            print("\nERROR querying Notion database")
            print(
                f"Database: {database_id[:8]}..."
            )
            print(
                f"HTTP status: {response.status_code}"
            )
            print(response.text)

            response.raise_for_status()

        data = response.json()

        results.extend(
            data.get("results", [])
        )

        if not data.get("has_more"):
            break

        payload["start_cursor"] = (
            data["next_cursor"]
        )

    return results


def plain_text(
    prop: dict[str, Any],
) -> Optional[str]:
    """Read title or rich_text content."""

    prop_type = prop.get("type")

    if prop_type == "title":
        values = prop.get("title", [])

    elif prop_type == "rich_text":
        values = prop.get(
            "rich_text",
            [],
        )

    else:
        return None

    value = "".join(
        item.get("plain_text", "")
        for item in values
    ).strip()

    return value or None


def select_name(
    prop: dict[str, Any],
) -> Optional[str]:
    """Read a Notion select or status property."""

    prop_type = prop.get("type")

    if prop_type == "select":
        value = prop.get("select")

    elif prop_type == "status":
        value = prop.get("status")

    else:
        return None

    return (
        value.get("name")
        if value
        else None
    )


def checkbox_value(
    prop: dict[str, Any],
    default: bool = False,
) -> bool:
    """Read a Notion checkbox."""

    if prop.get("type") != "checkbox":
        return default

    return bool(
        prop.get(
            "checkbox",
            default,
        )
    )


def date_value(
    prop: dict[str, Any],
) -> Optional[datetime]:
    """Read a Notion date start value."""

    if prop.get("type") != "date":
        return None

    value = prop.get("date")

    if not value:
        return None

    start = value.get("start")

    if not start:
        return None

    return datetime.fromisoformat(
        start.replace(
            "Z",
            "+00:00",
        )
    )


def number_value(
    prop: dict[str, Any],
) -> Optional[int]:
    """Read a Notion number property."""

    if prop.get("type") != "number":
        return None

    value = prop.get("number")

    if value is None:
        return None

    return int(value)


def relation_ids(
    prop: dict[str, Any],
) -> list[str]:
    """Return related Notion page IDs."""

    if prop.get("type") != "relation":
        return []

    return [
        item["id"]
        for item in prop.get(
            "relation",
            [],
        )
        if item.get("id")
    ]


def multi_select_names(
    prop: dict[str, Any],
) -> list[str]:
    """Read names from a Notion multi_select property."""

    if prop.get("type") != "multi_select":
        return []

    return [
        item.get("name")
        for item in prop.get(
            "multi_select",
            [],
        )
        if item.get("name")
    ]


def optional_iso_date(
    prop: dict[str, Any],
) -> Optional[str]:
    """Return a Notion date as an ISO string for legacy metadata."""

    value = date_value(prop)

    return (
        value.isoformat()
        if value
        else None
    )


# ---------------------------------------------------------------------------
# Notion -> AIOS domain models
# ---------------------------------------------------------------------------

def notion_project_to_model(
    page: dict[str, Any],
) -> Project:

    props = page.get(
        "properties",
        {},
    )

    legacy_metadata = {
        "area": select_name(
            props.get("Area", {})
        ),
        "priority": select_name(
            props.get("Priority", {})
        ),
        "project_type": select_name(
            props.get("Project Type", {})
        ),
    }

    legacy_metadata = {
        key: value
        for key, value in legacy_metadata.items()
        if value is not None
    }

    return Project(
        id=page["id"],
        legacy_notion_id=page["id"],

        name=(
            plain_text(
                props.get(
                    "Project Name",
                    {},
                )
            )
            or "(Untitled Project)"
        ),

        status=select_name(
            props.get(
                "Status",
                {},
            )
        ),

        is_active=checkbox_value(
            props.get(
                "Active",
                {},
            )
        ),

        legacy_metadata=legacy_metadata,

        created_at=datetime.fromisoformat(
            page["created_time"].replace(
                "Z",
                "+00:00",
            )
        ),

        updated_at=datetime.fromisoformat(
            page["last_edited_time"].replace(
                "Z",
                "+00:00",
            )
        ),
    )


def notion_task_to_model(
    page: dict[str, Any],
) -> Task:

    props = page.get(
        "properties",
        {},
    )

    project_ids = relation_ids(
        props.get(
            "Project",
            {},
        )
    )

    parent_ids = relation_ids(
        props.get(
            "Parent Task",
            {},
        )
    )

    suggested_project = plain_text(
        props.get(
            "Suggested Project",
            {},
        )
    )

    legacy_metadata = {
        "do": select_name(
            props.get("Do", {})
        ),

        "do_date": optional_iso_date(
            props.get("Do Date", {})
        ),

        "priority": select_name(
            props.get("Priority", {})
        ),

        "task_type": select_name(
            props.get("Task Type", {})
        ),

        "who": select_name(
            props.get("Who", {})
        ),

        "tags": (
            multi_select_names(
                props.get("Tags", {})
            )
            or None
        ),

        "reviewed": (
            True
            if checkbox_value(
                props.get("Reviewed", {})
            )
            else None
        ),

        "ai_generated": (
            True
            if checkbox_value(
                props.get("AI Generated", {})
            )
            else None
        ),

        "duplicate": (
            True
            if checkbox_value(
                props.get("Duplicate", {})
            )
            else None
        ),

        "duplicate_notes": plain_text(
            props.get(
                "Duplicate notes",
                {},
            )
        ),

        "start": optional_iso_date(
            props.get("Start", {})
        ),

        "end": optional_iso_date(
            props.get("End", {})
        ),
    }

    legacy_metadata = {
        key: value
        for key, value in legacy_metadata.items()
        if value not in (
            None,
            [],
            {},
        )
    }

    return Task(
        id=page["id"],
        legacy_notion_id=page["id"],

        title=(
            plain_text(
                props.get(
                    "Task Name",
                    {},
                )
            )
            or "(Untitled Task)"
        ),

        is_open=checkbox_value(
            props.get(
                "Open Loop",
                {},
            ),
            True,
        ),

        is_done=checkbox_value(
            props.get(
                "Done",
                {},
            )
        ),

        is_archived=checkbox_value(
            props.get(
                "Archived",
                {},
            )
        ),

        status=select_name(
            props.get(
                "Status",
                {},
            )
        ),

        importance=select_name(
            props.get(
                "Importance",
                {},
            )
        ),

        urgency=select_name(
            props.get(
                "Urgency",
                {},
            )
        ),

        effort=select_name(
            props.get(
                "Effort",
                {},
            )
        ),

        duration=select_name(
            props.get(
                "Duration",
                {},
            )
        ),

        due_at=date_value(
            props.get(
                "Due Date",
                {},
            )
        ),

        defer_until=date_value(
            props.get(
                "Defer Until",
                {},
            )
        ),

        is_just_do_it=checkbox_value(
            props.get(
                "Just Do It",
                {},
            )
        ),

        is_quick_win=checkbox_value(
            props.get(
                "Quick Win",
                {},
            )
        ),

        suggested_project=suggested_project,

        project_id=(
            project_ids[0]
            if project_ids
            else None
        ),

        parent_task_id=(
            parent_ids[0]
            if parent_ids
            else None
        ),

        step_order=number_value(
            props.get(
                "Step Order",
                {},
            )
        ),

        legacy_metadata=legacy_metadata,

        created_at=datetime.fromisoformat(
            page["created_time"].replace(
                "Z",
                "+00:00",
            )
        ),

        updated_at=datetime.fromisoformat(
            page["last_edited_time"].replace(
                "Z",
                "+00:00",
            )
        ),
    )


# ---------------------------------------------------------------------------
# Representative sample selection
# ---------------------------------------------------------------------------

def select_representative_tasks(
    tasks: list[Task],
    limit: int,
) -> list[Task]:

    selected: list[Task] = []
    selected_ids: set[str] = set()

    def add_matching(
        predicate: Callable[[Task], bool],
        count: int,
    ) -> None:

        added = 0

        for task in tasks:

            if len(selected) >= limit:
                return

            if task.id in selected_ids:
                continue

            if not predicate(task):
                continue

            selected.append(task)
            selected_ids.add(task.id)

            added += 1

            if added >= count:
                return

    add_matching(
        lambda t:
            t.is_open
            and not t.is_done
            and not t.is_archived
            and bool(t.project_id),
        4,
    )

    add_matching(
        lambda t:
            t.is_open
            and not t.is_done
            and not t.is_archived
            and not t.project_id,
        4,
    )

    add_matching(
        lambda t:
            t.is_quick_win
            and t.is_open
            and not t.is_done
            and not t.is_archived,
        3,
    )

    add_matching(
        lambda t:
            t.due_at is not None
            and t.is_open
            and not t.is_done,
        3,
    )

    add_matching(
        lambda t:
            t.defer_until is not None
            and not t.is_done,
        2,
    )

    add_matching(
        lambda t:
            t.parent_task_id is not None,
        3,
    )

    add_matching(
        lambda t:
            t.is_done,
        2,
    )

    add_matching(
        lambda t:
            t.is_archived,
        2,
    )

    add_matching(
        lambda t:
            t.is_just_do_it,
        2,
    )

    add_matching(
        lambda t:
            t.is_open
            and not t.is_done
            and not t.is_archived,
        limit,
    )

    return selected[:limit]


# ---------------------------------------------------------------------------
# Repository-backed Supabase migration
# ---------------------------------------------------------------------------

def upsert_projects(
    repository: ProjectRepository,
    projects: list[Project],
) -> dict[str, str]:

    print(
        "\nWriting projects through "
        "ProjectRepository..."
    )

    stored_projects = (
        repository.upsert_projects(
            projects
        )
    )

    project_map: dict[str, str] = {}

    for project in stored_projects:

        if (
            project.legacy_notion_id
            and project.id
        ):
            project_map[
                project.legacy_notion_id
            ] = project.id

    print(
        "Projects available through repository: "
        f"{repository.count_projects()}"
    )

    return project_map


def upsert_sample_tasks(
    repository: TaskRepository,
    tasks: list[Task],
    project_map: dict[str, str],
) -> dict[str, str]:

    print(
        "\nWriting task sample through "
        "TaskRepository..."
    )

    task_map: dict[str, str] = {}

    for task in tasks:

        supabase_project_id = None

        if task.project_id:
            supabase_project_id = (
                project_map.get(
                    task.project_id
                )
            )

            if not supabase_project_id:
                print(
                    "WARNING: Missing project "
                    f"mapping for {task.title!r}"
                )

        stored_task = (
            repository.upsert_task(
                replace(
                    task,
                    project_id=
                        supabase_project_id,
                    parent_task_id=None,
                )
            )
        )

        if task.legacy_notion_id:
            task_map[
                task.legacy_notion_id
            ] = stored_task.id

    print(
        "Tasks available through repository: "
        f"{repository.count_tasks()}"
    )

    return task_map


def apply_parent_relationships(
    repository: TaskRepository,
    tasks: list[Task],
    task_map: dict[str, str],
) -> int:

    updated = 0

    for task in tasks:

        if not task.parent_task_id:
            continue

        if not task.legacy_notion_id:
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

        if not child_supabase_id:
            continue

        if not parent_supabase_id:
            print(
                "Parent not in POC sample; "
                f"leaving parent unset for "
                f"{task.title!r}"
            )
            continue

        repository.update_parent_task(
            child_supabase_id,
            parent_supabase_id,
        )

        updated += 1

    return updated


# ---------------------------------------------------------------------------
# Reporting / validation
# ---------------------------------------------------------------------------

def print_dry_run_summary(
    projects: list[Project],
    tasks: list[Task],
    sample: list[Task],
) -> None:

    open_tasks = [
        task
        for task in tasks
        if (
            task.is_open
            and not task.is_done
            and not task.is_archived
        )
    ]

    project_tasks = [
        task
        for task in tasks
        if task.project_id
    ]

    parent_tasks = [
        task
        for task in tasks
        if task.parent_task_id
    ]

    quick_wins = [
        task
        for task in tasks
        if task.is_quick_win
    ]

    suggested = [
        task
        for task in tasks
        if task.suggested_project
    ]

    metadata_tasks = [
        task
        for task in tasks
        if task.legacy_metadata
    ]

    print("\nPOC summary:")

    print(
        f"  Total projects:       "
        f"{len(projects)}"
    )

    print(
        f"  Total tasks:          "
        f"{len(tasks)}"
    )

    print(
        f"  Open tasks:           "
        f"{len(open_tasks)}"
    )

    print(
        f"  Tasks with projects:  "
        f"{len(project_tasks)}"
    )

    print(
        f"  Tasks with parents:   "
        f"{len(parent_tasks)}"
    )

    print(
        f"  Quick Win tasks:      "
        f"{len(quick_wins)}"
    )

    print(
        f"  Suggested projects:   "
        f"{len(suggested)}"
    )

    print(
        f"  Tasks with metadata:  "
        f"{len(metadata_tasks)}"
    )

    print(
        f"  POC task sample:      "
        f"{len(sample)}"
    )

    print("\nSelected POC tasks:")

    for index, task in enumerate(
        sample,
        start=1,
    ):

        flags: list[str] = []

        if (
            task.is_open
            and not task.is_done
            and not task.is_archived
        ):
            flags.append("open")

        if task.is_done:
            flags.append("done")

        if task.is_archived:
            flags.append("archived")

        if task.is_quick_win:
            flags.append("quick-win")

        if task.is_just_do_it:
            flags.append("just-do-it")

        if task.project_id:
            flags.append("project")

        if task.parent_task_id:
            flags.append("subtask")

        if task.due_at:
            flags.append("due")

        if task.defer_until:
            flags.append("deferred")

        if task.suggested_project:
            flags.append("suggested-project")

        if task.legacy_metadata:
            flags.append("legacy-metadata")

        print(
            f"  {index:02d}. "
            f"{task.title} "
            f"[{', '.join(flags)}]"
        )


def validate_supabase(
    project_repository: ProjectRepository,
    task_repository: TaskRepository,
    expected_projects: int,
    sample: list[Task],
) -> None:

    projects = (
        project_repository
        .get_all_projects()
    )

    tasks = (
        task_repository
        .get_all_tasks()
    )

    sample_notion_ids = {
        task.legacy_notion_id
        for task in sample
        if task.legacy_notion_id
    }

    imported_sample = [
        task
        for task in tasks
        if task.legacy_notion_id
        in sample_notion_ids
    ]

    linked_projects = sum(
        1
        for task in imported_sample
        if task.project_id
    )

    linked_parents = sum(
        1
        for task in imported_sample
        if task.parent_task_id
    )

    suggested_projects = sum(
        1
        for task in imported_sample
        if task.suggested_project
    )

    metadata_tasks = sum(
        1
        for task in imported_sample
        if task.legacy_metadata
    )

    print("\nRepository validation:")

    print(
        f"  Projects in Supabase: "
        f"{len(projects)}"
    )

    print(
        f"  Expected projects:    "
        f"{expected_projects}"
    )

    print(
        f"  Sample tasks found:   "
        f"{len(imported_sample)}"
    )

    print(
        f"  Expected sample:      "
        f"{len(sample)}"
    )

    print(
        f"  Project links:        "
        f"{linked_projects}"
    )

    print(
        f"  Parent links:         "
        f"{linked_parents}"
    )

    print(
        f"  Suggested projects:   "
        f"{suggested_projects}"
    )

    print(
        f"  Metadata-bearing:     "
        f"{metadata_tasks}"
    )

    if len(projects) != expected_projects:
        raise RuntimeError(
            "Project count mismatch."
        )

    if len(imported_sample) != len(sample):
        raise RuntimeError(
            "Sample task count mismatch."
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description=(
            "AIOS Notion -> Supabase "
            "repository migration POC"
        )
    )

    parser.add_argument(
        "--write",
        action="store_true",
        help=(
            "Actually write POC data to Supabase. "
            "Without this flag the script is read-only."
        ),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help=(
            "Maximum number of representative "
            "tasks to import. Default: 25."
        ),
    )

    return parser.parse_args()


def main() -> None:

    args = parse_args()

    if args.limit < 1:
        raise ValueError(
            "--limit must be at least 1"
        )

    print("=" * 64)
    print("AIOS SUPABASE MIGRATION POC")
    print("=" * 64)

    if args.write:
        print(
            "MODE: REPOSITORY-BACKED "
            "CONTROLLED WRITE"
        )
    else:
        print(
            "MODE: DRY RUN — "
            "NO SUPABASE WRITES"
        )

    print(
        "Notion is read-only in both modes."
    )

    if not TASKS_DATABASE_ID:
        raise RuntimeError(
            "Tasks database ID is not configured."
        )

    if not PROJECTS_DATABASE_ID:
        raise RuntimeError(
            "Projects database ID is not configured."
        )

    print("\nReading Notion Projects...")

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

    print("\nReading Notion Tasks...")

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

    sample = select_representative_tasks(
        tasks,
        args.limit,
    )

    print_dry_run_summary(
        projects,
        tasks,
        sample,
    )

    if not args.write:

        print(
            "\nDry run completed successfully."
        )

        print(
            "No Supabase records were changed."
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

    project_map = upsert_projects(
        project_repository,
        projects,
    )

    task_map = upsert_sample_tasks(
        task_repository,
        sample,
        project_map,
    )

    parent_count = (
        apply_parent_relationships(
            task_repository,
            sample,
            task_map,
        )
    )

    print(
        "\nParent relationships applied: "
        f"{parent_count}"
    )

    validate_supabase(
        project_repository,
        task_repository,
        expected_projects=len(projects),
        sample=sample,
    )

    print("\n" + "=" * 64)
    print("REPOSITORY POC WRITE COMPLETED")
    print("=" * 64)

    print(
        "\nNotion was not modified."
    )


if __name__ == "__main__":
    main()