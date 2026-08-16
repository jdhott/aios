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
    project_context: str | None = None,
    project_anchor_title: str | None = None,
    completed_work: list[str] | None = None,
    open_work: list[str] | None = None,
    completed_activation_steps: list[str] | None = None,
    proposal_feedback: list[dict[str, Any]] | None = None,
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
    project_context = str(project_context or "").strip()
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

    proposal_feedback = [
        {
            "title": str(item.get("title") or "").strip(),
            "feedback": str(item.get("feedback") or "").strip(),
        }
        for item in (proposal_feedback or [])
        if str(item.get("feedback") or "").strip()
    ]

    feedback_text = "\n".join(
        f"- Previous proposal: {item['title']}\n"
        f"  User feedback: {item['feedback']}"
        for item in proposal_feedback
    ) or "(No previous proposal feedback.)"

    latest_feedback = (
        proposal_feedback[0]
        if proposal_feedback
        else None
    )

    latest_feedback_text = (
        (
            f"Rejected proposal:\n{latest_feedback['title']}\n\n"
            f"User correction:\n{latest_feedback['feedback']}"
        )
        if latest_feedback
        else "(No current correction.)"
    )

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

Known project context:
{project_context or "(No additional project context provided.)"}

Project anchor / outcome:
{project_anchor_title or "(No separate anchor provided.)"}

Completed project work:
{completed_text}

Current open project work:
{open_text}

Completed activation history:
{activation_text}

Most recent rejected proposal and binding correction:
{latest_feedback_text}

Earlier proposal feedback:
{feedback_text}

Determine whether there is useful project work that can actually be done now.

Return JSON only in exactly one of these forms:

{{"state":"actionable","tasks":[{{"title":"..."}}]}}

or

{{"state":"waiting","tasks":[]}}

Rules:
- Treat the Known project context as authoritative facts, decisions, and constraints.
- The most recent User correction is binding. The replacement must directly fix the specific problems the user identified.
- Follow explicit instructions in the User correction literally, including scope, sequencing, required actions, forbidden actions, and wording/length constraints.
- Do not preserve a rejected action by substituting a synonym or equivalent action. For example, if the user says not to distribute something yet, do not replace "distribute" with "send", "share", "circulate", "deliver", or an equivalent action.
- Earlier proposal feedback should also be used to avoid repeating previously rejected approaches.
- Proposal feedback is authoritative about the user's desired approach, but it is not automatically an authoritative project fact unless the Known project context also establishes that fact.
- Do not propose work that contradicts the Known project context.
- Do not invent missing requirements merely because they are common for this type of project.
- Do not infer that a project needs common optional elements such as decorations, entertainment, catering, gifts, seating plans, themes, or supplies unless the Known project context supports them.
- A task is executable now only if all information required to start and meaningfully advance it is already available. Do not propose work that depends on pending RSVPs, unknown preferences, final headcounts, future replies, or other unresolved information.
- Prefer tasks that follow directly from known facts or unfinished decisions in the Known project context.
- If the Known project context and work history do not establish enough remaining executable work, return a waiting state rather than inventing conventional project tasks.
- Tasks must be genuine project tasks, not tiny activation/JDI steps.
- Each proposed task must advance the project outcome.
- Each task must be executable now without waiting for another person, reply, delivery, approval, future date, or external event.
- Do not create a task that merely says to wait, monitor, check later, or review something that does not yet exist.
- Do not repeat or substantially duplicate completed project work, open project work, or completed activation history.
- Do not recreate the project anchor or restate the project outcome as a task.
- Do not invent people, deadlines, places, preferences, decisions, or facts not provided.
- Prefer 1 to 3 concrete project tasks.
- Every proposed task title must be 75 characters or fewer, including spaces.
- Prefer direct task wording. Do not pack explanation, rationale, or later steps into the title.
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
                + [
                    item["title"]
                    for item in proposal_feedback
                    if item["title"]
                ]
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

            if len(title) > 75:
                print(
                    "[Project Work] Rejected generated title over "
                    f"75 characters: {title}"
                )
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
            return {
                "state": "waiting",
                "tasks": [],
            }

        validated_tasks = validate_project_work_candidates(
            client,
            project_name=project_name,
            project_context=project_context,
            completed_work=completed_work,
            open_work=open_work,
            completed_activation_steps=completed_activation_steps,
            proposal_feedback=proposal_feedback,
            candidates=tasks,
        )

        if not validated_tasks:
            print(
                "[Project Work] No generated candidates passed "
                "grounding validation."
            )
            return {
                "state": "waiting",
                "tasks": [],
            }

        return {
            "state": "actionable",
            "tasks": validated_tasks,
        }

    except Exception as exc:
        print(
            f"[Project Work] AI generation failed: {exc}"
        )
        return None


def validate_project_work_candidates(
    client,
    *,
    project_name: str,
    project_context: str | None,
    completed_work: list[str] | None,
    open_work: list[str] | None,
    completed_activation_steps: list[str] | None,
    proposal_feedback: list[dict[str, Any]] | None = None,
    candidates: list[dict[str, str]],
) -> list[dict[str, str]]:
    """
    Strictly validate proposed project tasks against known project state.

    A plausible task is not enough. It must be grounded in known facts and
    executable now. Validation fails closed.
    """
    if client is None or not candidates:
        return []

    project_context = str(project_context or "").strip()

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

    proposal_feedback = [
        {
            "title": str(item.get("title") or "").strip(),
            "feedback": str(item.get("feedback") or "").strip(),
        }
        for item in (proposal_feedback or [])
        if str(item.get("feedback") or "").strip()
    ]

    feedback_text = "\n".join(
        f"- Previous proposal: {item['title']}\n"
        f"  User feedback: {item['feedback']}"
        for item in proposal_feedback
    ) or "(none)"

    latest_feedback = (
        proposal_feedback[0]
        if proposal_feedback
        else None
    )

    latest_feedback_text = (
        (
            f"Rejected proposal:\n{latest_feedback['title']}\n\n"
            f"User correction:\n{latest_feedback['feedback']}"
        )
        if latest_feedback
        else "(none)"
    )

    candidate_lines = "\n".join(
        f"C{index}: {item['title']}"
        for index, item in enumerate(candidates, start=1)
    )

    history = "\n".join(
        f"- {item}"
        for item in (
            completed_work
            + open_work
            + completed_activation_steps
        )
    ) or "(none)"

    model = os.getenv(
        "AIOS_PROJECT_WORK_MODEL",
        os.getenv(
            "AIOS_FOCUS_GUIDANCE_MODEL",
            "gpt-4.1-mini",
        ),
    )

    prompt = f"""You are a strict validator of proposed tasks for ONE project.

Project:
{project_name}

Authoritative known project context:
{project_context or "(none)"}

Known task/work history:
{history}

Most recent rejected proposal and binding correction:
{latest_feedback_text}

Earlier proposal feedback:
{feedback_text}

Candidate tasks:
{candidate_lines}

Return JSON only:
{{"approved":["C1"],"rejected":[{{"id":"C2","reason":"..."}}]}}

STRICT RULES:
- Approve a task only when the known context, history, or explicit user proposal feedback provides sufficient basis for doing it.
- The most recent User correction is binding. Reject any candidate that violates or only partially follows it.
- Reject synonym workarounds that preserve an action the user explicitly rejected.
- Reject any candidate title longer than 75 characters.
- User proposal feedback may establish the preferred approach to the work, but do not treat unsupported factual details within it as durable project facts.
- Common or conventional activities for this type of project are NOT evidence.
- Reject tasks that introduce unsupported assumptions, requirements, preferences, or optional elements.
- Reject tasks requiring information that is still unresolved or pending.
- Reject a task if it assumes that required information, commitments, responses, documents, materials, or decisions already exist when the Known project context or work history does not explicitly establish that they exist.
- Do not interpret "in progress", "coming in", or "pending" as meaning that enough information exists to complete a dependent task.
- Reject tasks that depend on future replies, RSVPs, final headcounts, unknown preferences, approvals, deliveries, or future events.
- Reject work already completed or substantially duplicated.
- The task must be useful and executable now.
- When uncertain, REJECT.
- It is completely valid to approve none.
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
        approved_ids = {
            str(item).strip()
            for item in (data.get("approved") or [])
        }

        approved = []

        for index, candidate in enumerate(candidates, start=1):
            if f"C{index}" in approved_ids:
                approved.append(candidate)

        return approved

    except Exception as exc:
        print(
            f"[Project Work] Candidate validation failed: {exc}"
        )
        return []
