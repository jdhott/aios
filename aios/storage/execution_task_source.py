from __future__ import annotations

from typing import Any, Optional

from aios.models import Task
from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_repository import TaskRepository


def _title_property(value: str) -> dict[str, Any]:
    return {
        "type": "title",
        "title": [
            {
                "plain_text": value,
                "text": {"content": value},
            }
        ],
    }


def _select_property(value: Optional[str]) -> dict[str, Any]:
    return {
        "type": "select",
        "select": {"name": value} if value else None,
    }


def _checkbox_property(value: bool) -> dict[str, Any]:
    return {"type": "checkbox", "checkbox": bool(value)}


def _date_property(value) -> dict[str, Any]:
    return {
        "type": "date",
        "date": {"start": value.isoformat()} if value else None,
    }


def _number_property(value: Optional[int | float]) -> dict[str, Any]:
    return {"type": "number", "number": value}


def _notion_number(props: dict[str, Any], name: str) -> Optional[int | float]:
    prop = props.get(name, {})
    if prop.get("type") != "number":
        return None
    return prop.get("number")


def _notion_checkbox(props: dict[str, Any], name: str) -> bool:
    prop = props.get(name, {})
    if prop.get("type") != "checkbox":
        return False
    return prop.get("checkbox") is True


def build_notion_execution_state(
    notion_tasks: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Extract mutable execution/presentation state from caller-supplied Notion tasks."""
    state: dict[str, dict[str, Any]] = {}

    for page in notion_tasks:
        notion_id = page.get("id")
        if not notion_id:
            continue

        props = page.get("properties", {})
        state[notion_id] = {
            "execution_score": _notion_number(props, "Execution Score"),
            "execution_rank": _notion_number(props, "Execution Rank"),
            "best_next_action": _notion_checkbox(props, "Best Next Action"),
            "surfaced_quick_win": _notion_checkbox(props, "Surfaced Quick Win"),
        }

    return state


def task_to_legacy_execution_payload(
    task: Task,
    execution_state: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Convert a Supabase Task to the temporary Notion-shaped execution payload."""
    execution_state = execution_state or {}

    return {
        "id": task.legacy_notion_id or task.id,
        "_supabase_id": task.id,
        "_source": "supabase",
        "properties": {
            "Task Name": _title_property(task.title),
            "Open Loop": _checkbox_property(task.is_open),
            "Done": _checkbox_property(task.is_done),
            "Archived": _checkbox_property(task.is_archived),
            "Status": _select_property(task.status),
            "Importance": _select_property(task.importance),
            "Urgency": _select_property(task.urgency),
            "Effort": _select_property(task.effort),
            "Duration": _select_property(task.duration),
            "Due Date": _date_property(task.due_at),
            "Defer Until": _date_property(task.defer_until),
            "Just Do It": _checkbox_property(task.is_just_do_it),
            "Quick Win": _checkbox_property(task.is_quick_win),
            "Execution Score": _number_property(
                execution_state.get("execution_score")
            ),
            "Execution Rank": _number_property(
                execution_state.get("execution_rank")
            ),
            "Best Next Action": _checkbox_property(
                bool(execution_state.get("best_next_action", False))
            ),
            "Surfaced Quick Win": _checkbox_property(
                bool(execution_state.get("surfaced_quick_win", False))
            ),
        },
    }


def get_supabase_execution_tasks(
    notion_execution_state_tasks: Optional[list[dict[str, Any]]] = None,
) -> list[dict[str, Any]]:
    """
    Load non-done task data from Supabase and overlay caller-supplied Notion
    execution state. This module performs no direct Notion API access.
    """
    print("[Execution Task Source] Loading durable task data from Supabase")

    repository = TaskRepository(SupabaseStore())
    all_tasks = repository.get_all_tasks()

    execution_population = [task for task in all_tasks if not task.is_done]

    print(
        "[Execution Task Source] "
        f"Supabase non-done task population: {len(execution_population)}"
    )

    notion_state = build_notion_execution_state(
        notion_execution_state_tasks or []
    )

    print(
        "[Execution Task Source] "
        f"Caller-supplied Notion execution state: {len(notion_state)} task(s)"
    )

    payloads: list[dict[str, Any]] = []
    missing_state = 0

    for task in execution_population:
        notion_id = task.legacy_notion_id
        state = notion_state.get(notion_id, {}) if notion_id else {}

        if notion_id and notion_id not in notion_state:
            missing_state += 1

        payloads.append(task_to_legacy_execution_payload(task, state))

    print(
        "[Execution Task Source] "
        f"Execution payloads created: {len(payloads)}"
    )
    print(
        "[Execution Task Source] "
        "Supabase tasks missing caller-supplied Notion execution state: "
        f"{missing_state}"
    )

    return payloads
