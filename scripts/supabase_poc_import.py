import os
from datetime import datetime
from typing import Any, Optional

import requests
from dotenv import load_dotenv

from aios.models import Project, Task

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


def query_database(database_id: str) -> list[dict[str, Any]]:
    """Read every record from a Notion database."""

    url = f"https://api.notion.com/v1/databases/{database_id}/query"

    payload = {"page_size": 100}
    results = []

    while True:
        response = requests.post(
            url,
            headers=NOTION_HEADERS,
            json=payload,
            timeout=30,
        )
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

    value = "".join(item.get("plain_text", "") for item in values).strip()

    return value or None


def select_name(prop: dict[str, Any]) -> Optional[str]:
    """Read either a Notion select or status value."""

    prop_type = prop.get("type")

    if prop_type == "select":
        value = prop.get("select")
    elif prop_type == "status":
        value = prop.get("status")
    else:
        return None

    return value.get("name") if value else None


def checkbox_value(prop: dict[str, Any], default: bool = False) -> bool:
    if prop.get("type") != "checkbox":
        return default

    return bool(prop.get("checkbox", default))


def date_value(prop: dict[str, Any]) -> Optional[datetime]:
    if prop.get("type") != "date":
        return None

    value = prop.get("date")

    if not value or not value.get("start"):
        return None

    return datetime.fromisoformat(value["start"].replace("Z", "+00:00"))


def number_value(prop: dict[str, Any]) -> Optional[int]:
    if prop.get("type") != "number":
        return None

    return prop.get("number")


def relation_ids(prop: dict[str, Any]) -> list[str]:
    if prop.get("type") != "relation":
        return []

    return [
        item["id"]
        for item in prop.get("relation", [])
        if item.get("id")
    ]


def notion_project_to_model(page: dict[str, Any]) -> Project:
    props = page.get("properties", {})

    return Project(
        id=page["id"],
        legacy_notion_id=page["id"],
        name=plain_text(props.get("Project Name", {})) or "(Untitled Project)",
        status=select_name(props.get("Status", {})),
        is_active=checkbox_value(props.get("Active", {})),
        created_at=datetime.fromisoformat(
            page["created_time"].replace("Z", "+00:00")
        ),
        updated_at=datetime.fromisoformat(
            page["last_edited_time"].replace("Z", "+00:00")
        ),
    )


def notion_task_to_model(page: dict[str, Any]) -> Task:
    props = page.get("properties", {})

    project_ids = relation_ids(props.get("Project", {}))
    parent_ids = relation_ids(props.get("Parent Task", {}))

    return Task(
        id=page["id"],
        legacy_notion_id=page["id"],
        title=plain_text(props.get("Task Name", {})) or "(Untitled Task)",

        is_open=checkbox_value(props.get("Open Loop", {}), True),
        is_done=checkbox_value(props.get("Done", {})),
        is_archived=checkbox_value(props.get("Archived", {})),

        status=select_name(props.get("Status", {})),

        importance=select_name(props.get("Importance", {})),
        urgency=select_name(props.get("Urgency", {})),
        effort=select_name(props.get("Effort", {})),
        duration=select_name(props.get("Duration", {})),

        due_at=date_value(props.get("Due Date", {})),
        defer_until=date_value(props.get("Defer Until", {})),

        is_just_do_it=checkbox_value(props.get("Just Do It", {})),
        is_quick_win=checkbox_value(props.get("Quick Win", {})),

        # Still Notion IDs during the POC.
        project_id=project_ids[0] if project_ids else None,
        parent_task_id=parent_ids[0] if parent_ids else None,

        step_order=number_value(props.get("Step Order", {})),

        created_at=datetime.fromisoformat(
            page["created_time"].replace("Z", "+00:00")
        ),
        updated_at=datetime.fromisoformat(
            page["last_edited_time"].replace("Z", "+00:00")
        ),
    )


def main():
    print("Supabase migration POC — DRY RUN")
    print("No Supabase records will be written.\n")

    if not PROJECTS_DATABASE_ID:
        raise RuntimeError("No Projects database ID is configured.")

    print("Reading Notion Projects...")
    project_pages = query_database(PROJECTS_DATABASE_ID)
    projects = [notion_project_to_model(page) for page in project_pages]

    print(f"Projects read: {len(projects)}")

    print("\nReading Notion Tasks...")
    task_pages = query_database(TASKS_DATABASE_ID)
    tasks = [notion_task_to_model(page) for page in task_pages]

    print(f"Tasks read: {len(tasks)}")

    print("\nSample projects:")
    for project in projects[:5]:
        print(
            f"  - {project.name!r} "
            f"status={project.status!r} "
            f"active={project.is_active}"
        )

    print("\nSample tasks:")
    for task in tasks[:10]:
        print(
            f"  - {task.title!r} "
            f"open={task.is_open} "
            f"done={task.is_done} "
            f"importance={task.importance!r} "
            f"project={task.project_id!r}"
        )

    open_tasks = [
        task
        for task in tasks
        if task.is_open and not task.is_done and not task.is_archived
    ]

    project_tasks = [task for task in tasks if task.project_id]
    parent_tasks = [task for task in tasks if task.parent_task_id]
    quick_wins = [task for task in tasks if task.is_quick_win]

    print("\nPOC summary:")
    print(f"  Total projects:       {len(projects)}")
    print(f"  Total tasks:          {len(tasks)}")
    print(f"  Open tasks:           {len(open_tasks)}")
    print(f"  Tasks with projects:  {len(project_tasks)}")
    print(f"  Tasks with parents:   {len(parent_tasks)}")
    print(f"  Quick Win tasks:      {len(quick_wins)}")

    print("\nDry run completed successfully.")


if __name__ == "__main__":
    main()