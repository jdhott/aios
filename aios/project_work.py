from __future__ import annotations

from datetime import datetime
from typing import Any

from aios.storage.supabase_store import SupabaseStore


PROJECT_WORK_SOURCE = "project_work"


def list_open_project_work(
    store: SupabaseStore,
    project_id: str,
) -> list[dict[str, Any]]:
    rows = (
        store.client
        .table("tasks")
        .select(
            "id,title,project_id,parent_task_id,task_role,"
            "is_open,is_done,is_archived,is_just_do_it,"
            "generated_source,importance,urgency,due_at,"
            "created_at,updated_at,completed_at"
        )
        .eq("project_id", project_id)
        .eq("generated_source", PROJECT_WORK_SOURCE)
        .eq("is_open", True)
        .eq("is_done", False)
        .eq("is_archived", False)
        .order("created_at")
        .execute()
        .data
        or []
    )

    return list(rows)


def create_supabase_project_task(
    store: SupabaseStore,
    *,
    title: str,
    project_id: str,
    importance: str | None = None,
    urgency: str | None = None,
    due_at: datetime | None = None,
) -> dict[str, Any]:
    """
    Create one normal Supabase-native task attached directly to an existing
    project.

    This is project work, not a JDI activation step:
      - project_id is set
      - parent_task_id is null
      - task_role is null
      - is_just_do_it is false
      - generated_source identifies project-work provenance
    """
    title = str(title or "").strip()
    project_id = str(project_id or "").strip()

    if not title:
        raise ValueError("Project task title is required.")

    if not project_id:
        raise ValueError("project_id is required.")

    response = (
        store.client
        .table("tasks")
        .insert({
            "legacy_notion_id": None,
            "title": title,
            "is_open": True,
            "is_done": False,
            "is_archived": False,
            "is_just_do_it": False,
            "is_quick_win": False,
            "importance": importance,
            "urgency": urgency,
            "due_at": (
                due_at.isoformat()
                if due_at
                else None
            ),
            "project_id": project_id,
            "parent_task_id": None,
            "step_order": None,
            "task_role": None,
            "generated_source": PROJECT_WORK_SOURCE,
        })
        .execute()
    )

    rows = response.data or []

    if not rows:
        raise RuntimeError(
            "Supabase project-task creation returned no row."
        )

    return dict(rows[0])


import json
import os


def generate_project_work(
    client,
    *,
    project_name: str,
    project_anchor_title: str | None = None,
    completed_work: list[str] | None = None,
    open_work: list[str] | None = None,
    completed_activation_steps: list[str] | None = None,
) -> dict[str, Any] | None:
    """
    Propose genuine executable project work.

    This does NOT create tasks and does NOT generate JDI activation steps.

    Valid results:
      {"state": "actionable", "tasks": [{"title": "..."}]}
      {"state": "waiting", "tasks": []}

    AI/parsing failures return None.
    """
    if client is None:
        return None

    project_name = str(project_name or "").strip()
    project_anchor_title = str(project_anchor_title or "").strip()

    completed_work = [
        str(item).strip()
        for item in (completed_work or [])
        if str(item).strip()
    ]

    open_work = [
        str(item).strip()
        for item in (open_work or [])
        if str(item).strip()
    ]

    completed_activation_steps = [
        str(item).strip()
        for item in (completed_activation_steps or [])
        if str(item).strip()
    ]

    def format_items(items: list[str], empty_text: str) -> str:
        if not items:
            return empty_text

        return "\n".join(
            f"{index}. {item}"
            for index, item in enumerate(items, start=1)
        )

    completed_text = format_items(
        completed_work,
        "(No completed project tasks recorded.)",
    )

    open_text = format_items(
        open_work,
        "(No open executable project tasks.)",
    )

    activation_text = format_items(
        completed_activation_steps,
        "(No completed activation history.)",
    )

    model = os.getenv(
        "AIOS_PROJECT_WORK_MODEL",
        os.getenv(
            "AIOS_FOCUS_GUIDANCE_MODEL",
            "gpt-4.1-mini",
        ),
    )

    prompt = f"""You are helping identify genuine executable work for ONE project.

Project:
{project_name}

Project anchor / outcome:
{project_anchor_title or "(No separate anchor provided.)"}

Completed project work:
{completed_text}

Current open project work:
{open_text}

Completed activation history:
{activation_text}

Determine whether there is useful project work that can actually be done now.

Return JSON only in exactly one of these forms:

{{"state":"actionable","tasks":[{{"title":"..."}}]}}

or

{{"state":"waiting","tasks":[]}}

Rules:
- Tasks must be genuine project tasks, not tiny activation/JDI steps.
- Each proposed task must advance the project outcome.
- Each task must be executable now without waiting for another person, reply, delivery, approval, future date, or external event.
- Do not create a task that merely says to wait, monitor, check later, or review something that does not yet exist.
- Do not repeat or substantially duplicate completed project work, open project work, or completed activation history.
- Do not recreate the project anchor or restate the project outcome as a task.
- Do not invent people, deadlines, places, preferences, decisions, or facts not provided.
- Prefer 1 to 3 concrete project tasks.
- These should be meaningful tasks that could later become a Best Next Action.
- Do not break tasks down into 5–15 minute starting moves; JDI activation is handled elsewhere.
- If nothing useful can currently be done, return state "waiting" with an empty tasks array.
"""

    try:
        response = client.responses.create(
            model=model,
            input=prompt,
        )

        raw = (response.output_text or "").strip()

        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()

        data = json.loads(raw)

        state = str(data.get("state") or "").strip().lower()

        if state == "waiting":
            return {
                "state": "waiting",
                "tasks": [],
            }

        if state != "actionable":
            return None

        raw_tasks = data.get("tasks") or []
        if not isinstance(raw_tasks, list):
            return None

        blocked_titles = {
            " ".join(item.lower().split())
            for item in (
                completed_work
                + open_work
                + completed_activation_steps
                + ([project_anchor_title] if project_anchor_title else [])
            )
        }

        tasks: list[dict[str, str]] = []
        seen: set[str] = set()

        for item in raw_tasks[:3]:
            if not isinstance(item, dict):
                continue

            title = str(item.get("title") or "").strip()
            if not title:
                continue

            normalized = " ".join(title.lower().split())

            if normalized in blocked_titles:
                continue

            if normalized in seen:
                continue

            seen.add(normalized)

            tasks.append({
                "title": title[:300],
            })

        if not tasks:
            return None

        return {
            "state": "actionable",
            "tasks": tasks,
        }

    except Exception as exc:
        print(
            f"[Project Work] AI generation failed: {exc}"
        )
        return None
