from __future__ import annotations

from datetime import datetime
from typing import Any

from aios.storage.supabase_store import SupabaseStore
from aios.temporal import serialize_task_datetime


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
            "due_at": serialize_task_datetime(due_at),
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
    project_outcome: str | None = None,
    project_context: str | None = None,
    project_anchor_title: str | None = None,
    completed_work: list[str] | None = None,
    open_work: list[str] | None = None,
    completed_activation_steps: list[str] | None = None,
    proposal_feedback: list[dict[str, Any]] | None = None,
    clarification_round: int = 0,
    allow_clarification: bool = False,
) -> dict[str, Any] | None:
    """
    Propose genuine executable project work.

    This does NOT create tasks and does NOT generate JDI activation steps.

    Valid results:
      {"state": "actionable", "tasks": [{"title": "..."}]}
      {"state": "waiting", "tasks": []}
      {"state": "clarification", "question": "...", "tasks": []}

    AI/parsing failures return None.
    """
    if client is None:
        return None

    project_name = str(project_name or "").strip()
    project_outcome = str(project_outcome or "").strip()
    project_context = str(project_context or "").strip()
    project_anchor_title = str(project_anchor_title or "").strip()

    # Project Outcome is now the canonical project-level goal.
    # The legacy project_anchor remains a backward-compatible fallback
    # while existing anchored projects are migrated.
    effective_outcome = (
        project_outcome
        or project_anchor_title
    )

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

Project outcome:
{effective_outcome or "(No explicit project outcome provided.)"}

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

Identify genuine MISSING project work that is not already represented in the current or completed work.

A valid project task does not need every fact required for its eventual completion. Research, comparison, decision, outreach, assessment, or information-gathering can itself be legitimate project work when the need for that work is grounded in the project outcome or Known project context.

Prefer work that can be STARTED now and meaningfully advances the project.

Return JSON only in exactly one of these forms:

{{"state":"actionable","tasks":[{{"title":"..."}}]}}

or

{{"state":"waiting","tasks":[]}}

or, only when clarification is allowed and one answer would materially change the work you propose:

{{"state":"clarification","question":"...","tasks":[]}}

Clarification available: {allow_clarification and clarification_round < 2}
Clarification round already used: {clarification_round} of 2

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
- A task is eligible when it can be started now and meaningfully advances the project. It does NOT need every fact required for eventual completion.
- Research, assessment, comparison, decision, outreach, quote/estimate gathering, or information-gathering are legitimate project tasks when they are directly grounded in the outcome or Known project context.
- An unresolved fact may itself justify a task to resolve that uncertainty. For example, if the context says a backwater valve is being investigated but necessity is not established, "Determine whether a backwater valve is warranted" is grounded work; "Install a backwater valve" is not yet grounded.
- Do not propose downstream work that assumes an unresolved decision, approval, response, delivery, preference, or requirement has already been resolved.
- Prefer tasks that follow directly from known facts, explicit uncertainties, or unfinished decisions in the Known project context.
- If one specific missing fact would materially change what useful work should be proposed, and clarification is available, ask ONE targeted question instead of guessing.
- Ask only about information that is genuinely consequential to identifying missing work; do not conduct a general project interview.
- If clarification is unavailable or no targeted question would help, return waiting rather than inventing conventional project tasks.
- Tasks must be genuine project tasks, not tiny activation/JDI steps.
- Each proposed task must advance the project outcome.
- Each task must be startable now. It may involve contacting another person, requesting an assessment/quote, or gathering information; do not reject such work merely because another person will later respond.
- Do not create a task that merely says to wait, monitor, check later, or perform downstream work that cannot begin until a future reply, approval, delivery, decision, date, or external event.
- Current open work is ALREADY PLANNED. Do not repeat, paraphrase, rename, or slightly broaden it.
- Completed work and completed activation history are ALREADY DONE. Do not recreate them.
- Before proposing a task, perform a gap check: identify what the outcome/context requires that is not already represented by open or completed work. Propose only that uncovered work.
- Proposed tasks must represent DISTINCT gaps. Do not return multiple tasks that address the same underlying need using different wording, scopes, or methods. If several candidates substantially overlap, return only the clearest and most useful one.
- Do not restate the project outcome as a task.
- Do not invent people, deadlines, places, preferences, decisions, or facts not provided.
- Prefer 1 to 3 concrete project tasks.
- Aim for task titles under 60 characters. Absolute maximum: 75 characters including spaces.
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

        print(
            f"[Project Work][Generator] project={project_name!r} "
            f"state={state or 'missing'}"
        )

        if state == "waiting":
            print(
                "[Project Work][Generator] No actionable candidates returned."
            )
            return {"state": "waiting", "tasks": []}

        if state == "clarification":
            question = str(data.get("question") or "").strip()
            if allow_clarification and clarification_round < 2 and question:
                return {"state": "clarification", "question": question[:500], "tasks": []}
            return {"state": "waiting", "tasks": []}

        if state != "actionable":
            return None

        raw_tasks = data.get("tasks") or []
        if not isinstance(raw_tasks, list):
            return None

        print(
            "[Project Work][Generator] Raw candidates:",
            [
                str(item.get("title") or "").strip()
                for item in raw_tasks
                if isinstance(item, dict)
            ],
        )

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
                print(
                    "[Project Work][Generator] BLOCKED existing/rejected work: "
                    f"{title}"
                )
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

        print(
            "[Project Work][Generator] Candidates sent to validator:",
            [item["title"] for item in tasks],
        )

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


def summarize_project_work_answer(client, *, project_context: str | None, question: str, answer: str) -> str | None:
    """Turn a clarification answer into concise durable project context."""
    if client is None or not str(answer or "").strip():
        return None
    model = os.getenv("AIOS_PROJECT_WORK_MODEL", os.getenv("AIOS_FOCUS_GUIDANCE_MODEL", "gpt-4.1-mini"))
    prompt = f"""Convert the user's answer into concise durable project context.

Existing project context:
{str(project_context or '').strip() or '(none)'}

Question AIOS asked:
{str(question or '').strip()}

User answer:
{str(answer or '').strip()}

Return JSON only: {{"context_update":"..."}}

Rules:
- Preserve the user's meaning exactly; do not invent facts or commitments.
- Preserve uncertainty such as probably, maybe, or not yet decided.
- Remove conversational filler and the question/answer framing.
- Keep important dates, people, quantities, constraints, decisions, and preferences.
- Write one concise reusable context statement, normally one or two sentences.
- Do not repeat facts already clearly present in Existing project context unless needed to make the new fact understandable.
"""
    try:
        response = client.responses.create(model=model, input=prompt)
        raw = (response.output_text or '').strip()
        if raw.startswith('```'):
            raw = raw.strip('`')
            if raw.lower().startswith('json'):
                raw = raw[4:].strip()
        data = json.loads(raw)
        value = str(data.get('context_update') or '').strip()
        return value[:1500] or None
    except Exception as exc:
        print(f"[Project Work] Context summary failed: {exc}")
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

    A plausible task is not enough. It must be grounded in known project
    state and represent meaningful missing work. Validation fails closed.
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
- The project name or project type by itself is NOT evidence that a conventional task is needed.
- For every candidate, identify the explicit basis for its need in the project outcome, Known project context, current/open work, completed work, or user proposal feedback. If no such basis exists, REJECT it even if the task would normally be sensible for this type of project.
- Reject tasks that introduce unsupported assumptions, requirements, preferences, or optional elements.
- Do NOT reject a task merely because information is unresolved when the task itself is grounded work to resolve that uncertainty through research, assessment, comparison, decision, outreach, or information gathering.
- Reject downstream work that assumes unresolved information, commitments, responses, documents, materials, approvals, preferences, deliveries, or decisions already exist.
- Do not interpret "in progress", "coming in", or "pending" as meaning an unresolved fact is already known.
- A task involving another person can be valid when the task itself is to contact them, request an assessment/quote, or gather information and that need is grounded in known project state.
- Project Work is a PROJECT PLAN, not a Best Next Action list. Do not reject an otherwise grounded missing task merely because another project task should logically happen first. Dependencies between sibling project tasks are allowed.
- Reject a downstream task only when an unresolved external fact, decision, approval, preference, response, or event could make the task unnecessary or materially change what the task should be.
- Reject work already completed or substantially duplicated. Also reject paraphrases or slight reformulations of current open work.
- Compare the candidate tasks with EACH OTHER. If two or more candidates address substantially the same underlying need or outcome, approve only one. Prefer the clearest, broadest useful formulation and reject the others as overlapping sibling work.
- The task must be useful, grounded, and genuinely missing.
- When uncertain whether the NEED for the task is grounded, REJECT. Do not reject merely because the task will produce information that is not yet known or because another sibling task may precede it.
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

        rejected_items = [
            item
            for item in (data.get("rejected") or [])
            if isinstance(item, dict)
        ]
        rejected_reasons = {
            str(item.get("id") or "").strip(): str(item.get("reason") or "").strip()
            for item in rejected_items
            if str(item.get("id") or "").strip()
        }

        approved = []

        for index, candidate in enumerate(candidates, start=1):
            candidate_id = f"C{index}"
            title = str(candidate.get("title") or "").strip()

            if candidate_id in approved_ids:
                print(
                    f"[Project Work][Validator] APPROVED {candidate_id}: {title}"
                )
                approved.append(candidate)
            else:
                reason = rejected_reasons.get(
                    candidate_id,
                    "(validator returned no rejection reason)",
                )
                print(
                    f"[Project Work][Validator] REJECTED {candidate_id}: "
                    f"{title} | reason={reason}"
                )

        return approved

    except Exception as exc:
        print(
            f"[Project Work] Candidate validation failed: {exc}"
        )
        return []
