"""
Supabase migration proof of concept.

Reads Projects and Tasks from the existing Notion databases and optionally
writes a controlled sample into Supabase.

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
from datetime import datetime
from typing import Any, Callable, Optional

import requests
from dotenv import load_dotenv

from aios.models import Project, Task
from aios.storage.supabase_store import SupabaseStore


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

def query_database(database_id: str) -> list[dict[str, Any]]:
    """Read every record from a Notion database."""

    if not database_id:
        raise RuntimeError("Notion database ID is not configured.")

    url = f"https://api.notion.com/v1/databases/{database_id}/query"

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
            print(f"Database: {database_id[:8]}...")
            print(f"HTTP status: {response.status_code}")
            print(response.text)
            response.raise_for_status()

        data = response.json()

        results.extend(data.get("results", []))

        if not data.get("has_more"):
            break

        payload["start_cursor"] = data["next_cursor"]

    return results


def plain_text(prop: dict[str, Any]) -> Optional[str]:
    """Read text from a Notion title or rich_text property."""

    prop_type = prop.get("type")

    if prop_type == "title":
        values = prop.get("title", [])
    elif prop_type == "rich_text":
        values = prop.get("rich_text", [])
    else:
        return None

    value = "".join(
        item.get("plain_text", "")
        for item in values
    ).strip()

    return value or None


def select_name(prop: dict[str, Any]) -> Optional[str]:
    """Read a Notion select or status property."""

    prop_type = prop.get("type")

    if prop_type == "select":
        value = prop.get("select")
    elif prop_type == "status":
        value = prop.get("status")
    else:
        return None

    return value.get("name") if value else None


def checkbox_value(
    prop: dict[str, Any],
    default: bool = False,
) -> bool:
    """Read a Notion checkbox."""

    if prop.get("type") != "checkbox":
        return default

    return bool(prop.get("checkbox", default))


def date_value(prop: dict[str, Any]) -> Optional[datetime]:
    """Read the start value from a Notion date property."""

    if prop.get("type") != "date":
        return None

    value = prop.get("date")

    if not value:
        return None

    start = value.get("start")

    if not start:
        return None

    return datetime.fromisoformat(
        start.replace("Z", "+00:00")
    )


def number_value(prop: dict[str, Any]) -> Optional[int]:
    """Read a Notion number property."""

    if prop.get("type") != "number":
        return None

    value = prop.get("number")

    if value is None:
        return None

    return int(value)


def relation_ids(prop: dict[str, Any]) -> list[str]:
    """Return related Notion page IDs."""

    if prop.get("type") != "relation":
        return []

    return [
        item["id"]
        for item in prop.get("relation", [])
        if item.get("id")
    ]


# ---------------------------------------------------------------------------
# Translation: Notion -> AIOS domain models
# ---------------------------------------------------------------------------

def notion_project_to_model(
    page: dict[str, Any],
) -> Project:

    props = page.get("properties", {})

    return Project(
        id=page["id"],
        legacy_notion_id=page["id"],
        name=(
            plain_text(props.get("Project Name", {}))
            or "(Untitled Project)"
        ),
        status=select_name(
            props.get("Status", {})
        ),
        is_active=checkbox_value(
            props.get("Active", {})
        ),
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

    props = page.get("properties", {})

    project_ids = relation_ids(
        props.get("Project", {})
    )

    parent_ids = relation_ids(
        props.get("Parent Task", {})
    )

    return Task(
        id=page["id"],
        legacy_notion_id=page["id"],

        title=(
            plain_text(props.get("Task Name", {}))
            or "(Untitled Task)"
        ),

        is_open=checkbox_value(
            props.get("Open Loop", {}),
            True,
        ),

        is_done=checkbox_value(
            props.get("Done", {})
        ),

        is_archived=checkbox_value(
            props.get("Archived", {})
        ),

        status=select_name(
            props.get("Status", {})
        ),

        importance=select_name(
            props.get("Importance", {})
        ),

        urgency=select_name(
            props.get("Urgency", {})
        ),

        effort=select_name(
            props.get("Effort", {})
        ),

        duration=select_name(
            props.get("Duration", {})
        ),

        due_at=date_value(
            props.get("Due Date", {})
        ),

        defer_until=date_value(
            props.get("Defer Until", {})
        ),

        is_just_do_it=checkbox_value(
            props.get("Just Do It", {})
        ),

        is_quick_win=checkbox_value(
            props.get("Quick Win", {})
        ),

        # During extraction these are still Notion IDs.
        # They are converted to Supabase UUIDs before writing.
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
            props.get("Step Order", {})
        ),

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
    """
    Select a deterministic cross-section of the task database.

    The goal is coverage, not randomness.
    """

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

    # Open tasks attached to projects
    add_matching(
        lambda t:
            t.is_open
            and not t.is_done
            and not t.is_archived
            and bool(t.project_id),
        4,
    )

    # Open unprojected tasks
    add_matching(
        lambda t:
            t.is_open
            and not t.is_done
            and not t.is_archived
            and not t.project_id,
        4,
    )

    # Quick Wins
    add_matching(
        lambda t:
            t.is_quick_win
            and t.is_open
            and not t.is_done
            and not t.is_archived,
        3,
    )

    # Tasks with due dates
    add_matching(
        lambda t:
            t.due_at is not None
            and t.is_open
            and not t.is_done,
        3,
    )

    # Deferred tasks
    add_matching(
        lambda t:
            t.defer_until is not None
            and not t.is_done,
        2,
    )

    # Child/subtasks
    add_matching(
        lambda t:
            t.parent_task_id is not None,
        3,
    )

    # Completed tasks
    add_matching(
        lambda t:
            t.is_done,
        2,
    )

    # Archived tasks
    add_matching(
        lambda t:
            t.is_archived,
        2,
    )

    # Just Do It tasks
    add_matching(
        lambda t:
            t.is_just_do_it,
        2,
    )

    # Fill remaining slots with open tasks
    add_matching(
        lambda t:
            t.is_open
            and not t.is_done
            and not t.is_archived,
        limit,
    )

    return selected[:limit]


# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------

def serialize_datetime(
    value: Optional[datetime],
) -> Optional[str]:

    return (
        value.isoformat()
        if value is not None
        else None
    )


def upsert_projects(
    store: SupabaseStore,
    projects: list[Project],
) -> dict[str, str]:
    """
    Upsert all Notion projects.

    Returns:
        {
            notion_project_id: supabase_project_uuid
        }
    """

    print("\nWriting projects to Supabase...")

    for project in projects:

        payload = {
            "legacy_notion_id":
                project.legacy_notion_id,

            "name":
                project.name,

            "status":
                project.status,

            "is_active":
                project.is_active,

            "created_at":
                serialize_datetime(
                    project.created_at
                ),

            "updated_at":
                serialize_datetime(
                    project.updated_at
                ),

            "completed_at":
                serialize_datetime(
                    project.completed_at
                ),
        }

        (
            store.client
            .table("projects")
            .upsert(
                payload,
                on_conflict="legacy_notion_id",
            )
            .execute()
        )

    # Fetch the authoritative Supabase UUID mapping.
    response = (
        store.client
        .table("projects")
        .select(
            "id, legacy_notion_id"
        )
        .execute()
    )

    project_map: dict[str, str] = {}

    for row in response.data or []:

        notion_id = row.get(
            "legacy_notion_id"
        )

        supabase_id = row.get("id")

        if notion_id and supabase_id:
            project_map[notion_id] = supabase_id

    print(
        f"Projects available in Supabase: "
        f"{len(project_map)}"
    )

    return project_map


def upsert_sample_tasks(
    store: SupabaseStore,
    tasks: list[Task],
    project_map: dict[str, str],
) -> dict[str, str]:
    """
    Insert/update the POC task sample.

    Parent relationships are intentionally omitted in this
    first pass and added later.
    """

    print("\nWriting task sample to Supabase...")

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
                    "WARNING: Project mapping missing "
                    f"for task {task.title!r}"
                )

        payload = {
            "legacy_notion_id":
                task.legacy_notion_id,

            "title":
                task.title,

            "is_open":
                task.is_open,

            "is_done":
                task.is_done,

            "is_archived":
                task.is_archived,

            "status":
                task.status,

            "importance":
                task.importance,

            "urgency":
                task.urgency,

            "effort":
                task.effort,

            "duration":
                task.duration,

            "due_at":
                serialize_datetime(
                    task.due_at
                ),

            "defer_until":
                serialize_datetime(
                    task.defer_until
                ),

            "is_just_do_it":
                task.is_just_do_it,

            "is_quick_win":
                task.is_quick_win,

            "project_id":
                supabase_project_id,

            # Added in second pass.
            "parent_task_id":
                None,

            "step_order":
                task.step_order,

            "created_at":
                serialize_datetime(
                    task.created_at
                ),

            "updated_at":
                serialize_datetime(
                    task.updated_at
                ),

            "completed_at":
                serialize_datetime(
                    task.completed_at
                ),
        }

        (
            store.client
            .table("tasks")
            .upsert(
                payload,
                on_conflict="legacy_notion_id",
            )
            .execute()
        )

    response = (
        store.client
        .table("tasks")
        .select(
            "id, legacy_notion_id"
        )
        .execute()
    )

    task_map: dict[str, str] = {}

    for row in response.data or []:

        notion_id = row.get(
            "legacy_notion_id"
        )

        supabase_id = row.get("id")

        if notion_id and supabase_id:
            task_map[notion_id] = supabase_id

    print(
        f"Tasks currently available in Supabase: "
        f"{len(task_map)}"
    )

    return task_map


def apply_parent_relationships(
    store: SupabaseStore,
    tasks: list[Task],
    task_map: dict[str, str],
) -> int:
    """
    Add parent_task_id relationships where both parent
    and child exist in the POC sample.
    """

    updated = 0

    for task in tasks:

        if not task.parent_task_id:
            continue

        child_supabase_id = (
            task_map.get(task.id)
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

        (
            store.client
            .table("tasks")
            .update({
                "parent_task_id":
                    parent_supabase_id
            })
            .eq(
                "id",
                child_supabase_id,
            )
            .execute()
        )

        updated += 1

    return updated


# ---------------------------------------------------------------------------
# Validation
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

    print("\nPOC summary:")
    print(
        f"  Total projects:       {len(projects)}"
    )
    print(
        f"  Total tasks:          {len(tasks)}"
    )
    print(
        f"  Open tasks:           {len(open_tasks)}"
    )
    print(
        f"  Tasks with projects:  {len(project_tasks)}"
    )
    print(
        f"  Tasks with parents:   {len(parent_tasks)}"
    )
    print(
        f"  Quick Win tasks:      {len(quick_wins)}"
    )

    print(
        f"  POC task sample:      {len(sample)}"
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

        flag_text = ", ".join(flags)

        print(
            f"  {index:02d}. "
            f"{task.title} "
            f"[{flag_text}]"
        )


def validate_supabase(
    store: SupabaseStore,
    expected_projects: int,
    sample: list[Task],
) -> None:

    projects_response = (
        store.client
        .table("projects")
        .select(
            "id, legacy_notion_id, name"
        )
        .execute()
    )

    tasks_response = (
        store.client
        .table("tasks")
        .select(
            (
                "id, legacy_notion_id, title, "
                "project_id, parent_task_id"
            )
        )
        .execute()
    )

    supabase_projects = (
        projects_response.data or []
    )

    supabase_tasks = (
        tasks_response.data or []
    )

    sample_notion_ids = {
        task.id
        for task in sample
    }

    imported_sample = [
        row
        for row in supabase_tasks
        if row.get("legacy_notion_id")
        in sample_notion_ids
    ]

    linked_projects = sum(
        1
        for row in imported_sample
        if row.get("project_id")
    )

    linked_parents = sum(
        1
        for row in imported_sample
        if row.get("parent_task_id")
    )

    print("\nSupabase validation:")
    print(
        f"  Projects in Supabase: "
        f"{len(supabase_projects)}"
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description=(
            "AIOS Notion -> Supabase migration POC"
        )
    )

    parser.add_argument(
        "--write",
        action="store_true",
        help=(
            "Actually write the POC data to Supabase. "
            "Without this flag the script is read-only."
        ),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help=(
            "Maximum number of representative tasks "
            "to import. Default: 25."
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
            "MODE: CONTROLLED WRITE TO SUPABASE"
        )
    else:
        print(
            "MODE: DRY RUN — NO SUPABASE WRITES"
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
            "\nNo Supabase records were changed."
        )

        print(
            "\nWhen ready, run:"
        )

        print(
            "  python -m "
            "scripts.supabase_poc_import "
            "--write"
        )

        return

    print(
        "\nConnecting to Supabase..."
    )

    store = SupabaseStore()

    health = store.health_check()

    print(
        f"Supabase connection: {health}"
    )

    project_map = upsert_projects(
        store,
        projects,
    )

    task_map = upsert_sample_tasks(
        store,
        sample,
        project_map,
    )

    parent_count = apply_parent_relationships(
        store,
        sample,
        task_map,
    )

    print(
        f"\nParent relationships applied: "
        f"{parent_count}"
    )

    validate_supabase(
        store,
        expected_projects=len(projects),
        sample=sample,
    )

    print("\n" + "=" * 64)
    print("POC WRITE COMPLETED")
    print("=" * 64)

    print(
        "\nNotion was not modified."
    )

    print(
        "Review the projects and tasks tables "
        "in Supabase before proceeding."
    )


if __name__ == "__main__":
    main()