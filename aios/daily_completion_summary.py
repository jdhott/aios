from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from zoneinfo import ZoneInfo

SUMMARY_MODEL = "gpt-4.1-mini"
SUMMARY_VERSION = "v2.0"
MIN_TASKS_FOR_AI_SUMMARY = 2


def _local_day_bounds(*, timezone_name: str = "America/Toronto", now: datetime | None = None):
    local_tz = ZoneInfo(timezone_name)
    current = now.astimezone(local_tz) if now else datetime.now(local_tz)
    day = current.date()
    local_start = datetime.combine(day, datetime.min.time(), tzinfo=local_tz)
    local_end = local_start + timedelta(days=1)
    return day, local_start.astimezone(timezone.utc), local_end.astimezone(timezone.utc)


def completion_fingerprint(tasks: list[dict]) -> str:
    parts = []
    for task in sorted(tasks, key=lambda row: str(row.get("id") or "")):
        parts.append(
            "|".join(
                [
                    str(task.get("id") or ""),
                    str(task.get("title") or "").strip(),
                    str(task.get("completed_at") or ""),
                ]
            )
        )
    material = SUMMARY_VERSION + "\n" + "\n".join(parts)
    return sha256(material.encode("utf-8")).hexdigest()


def load_completed_today(store, *, timezone_name: str = "America/Toronto", now: datetime | None = None) -> tuple[str, list[dict]]:
    day, start_utc, end_utc = _local_day_bounds(timezone_name=timezone_name, now=now)
    rows = (
        store.client.table("tasks")
        .select(
            "id,title,project_id,parent_task_id,generated_source,task_role,completed_at"
        )
        .eq("is_done", True)
        .eq("is_archived", False)
        .gte("completed_at", start_utc.isoformat())
        .lt("completed_at", end_utc.isoformat())
        .order("completed_at", desc=True)
        .execute()
        .data
        or []
    )
    tasks = [
        dict(row)
        for row in rows
        if row.get("generated_source") != "focus_activation"
        and row.get("task_role") != "focus_activation"
    ]

    project_ids = sorted({str(row.get("project_id")) for row in tasks if row.get("project_id")})
    if project_ids:
        project_rows = (
            store.client.table("projects").select("id,name").in_("id", project_ids).execute().data or []
        )
        project_titles = {
            str(row.get("id")): str(row.get("name") or "").strip()
            for row in project_rows
            if row.get("id")
        }
        for task in tasks:
            project_id = str(task.get("project_id") or "").strip()
            if project_id:
                task["project_title"] = project_titles.get(project_id) or None

    parent_ids = sorted({str(row.get("parent_task_id")) for row in tasks if row.get("parent_task_id")})
    if parent_ids:
        parent_rows = (
            store.client.table("tasks").select("id,title").in_("id", parent_ids).execute().data or []
        )
        parent_titles = {
            str(row.get("id")): str(row.get("title") or "").strip()
            for row in parent_rows
            if row.get("id")
        }
        for task in tasks:
            parent_id = str(task.get("parent_task_id") or "").strip()
            if parent_id:
                task["parent_title"] = parent_titles.get(parent_id) or None

    return day.isoformat(), tasks


def get_cached_daily_summary(store, *, summary_date: str, fingerprint: str) -> dict | None:
    rows = (
        store.client.table("daily_completion_summaries")
        .select("summary_date,fingerprint,summary,completed_count,generated_at")
        .eq("summary_date", summary_date)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        return None
    row = dict(rows[0])
    if str(row.get("fingerprint") or "") != fingerprint:
        return None
    return row


def _summary_prompt(tasks: list[dict]) -> str:
    lines = []
    for task in tasks:
        title = str(task.get("title") or "Untitled task").strip()
        context = []
        if task.get("project_title"):
            context.append(f"project: {task['project_title']}")
        if task.get("parent_title"):
            context.append(f"part of: {task['parent_title']}")
        suffix = f" ({'; '.join(context)})" if context else ""
        lines.append(f"- {title}{suffix}")
    return "\n".join(lines)


def generate_daily_summary(ai_client, tasks: list[dict]) -> str:
    if len(tasks) < MIN_TASKS_FOR_AI_SUMMARY:
        return ""
    response = ai_client.responses.create(
        model=SUMMARY_MODEL,
        input=(
            "Summarize today's completed work in one concise sentence; use two only when genuinely needed. "
            "Write directly about the work itself, not about the person doing it. "
            "Never say 'the user', 'they', 'them', 'their', or otherwise refer to the person in the third person. "
            "Use the meaningful theme or themes only as an internal selection mechanism for deciding what belongs in the summary. Never state, label, list, or explain the themes in the output. Output only the final retrospective prose. "
            "There may be one meaningful area of work or several equally important ones; do not force a primary-versus-secondary hierarchy. "
            "Before writing, silently decide which work would actually be worth remembering months later. Include only those meaningful themes. "
            "Judge significance by the substance of the work, not by how many completed items belong to a category. Several small routine chores should not outweigh one substantial block of project work. "
            "Routine chores, cleanup, maintenance, and minor administrative work may be omitted entirely, even when several such tasks were completed. The number of tasks in an area is not evidence that the area belongs in the summary. "
            "If one meaningful theme clearly dominates the day, summarize only that theme. Do not add minor routine work just to make the summary feel comprehensive. "
            "For example, if a day contains several substantial tasks advancing one project plus several ordinary household chores, summarize the substantial project work only. "
            "Prefer direct active phrasing without a subject, such as 'Prepared ingredients and levain...' rather than passive phrasing like 'Ingredients were prepared...' or third-person phrasing. "
            "Synthesize rather than enumerate. Do not list individual chores, every product, or every completed item unless one concrete example materially improves the summary. "
            "Omit routine or low-significance work entirely when more meaningful work already explains the day. A summary does not need to represent every category of completed work. "
            "Mention routine household, cleanup, maintenance, or administrative work only when it is itself a meaningful part of the day; when mentioned, compress it into a broad natural phrase rather than naming individual actions. "
            "Use plain, factual, natural journal language that will still be useful when read months later. "
            "Prefer a simple description of the work over internal project/category labels unless a project name is itself meaningful context. "
            "Do not embellish, dramatize, praise, or characterize how well, carefully, efficiently, or smoothly the work was performed. "
            "Do not infer motives, emotions, priorities, significance, or events that are not established by the completed work. "
            "Avoid report-style transitions such as 'Additionally' and decorative phrases such as 'centered on', 'intertwined', 'meticulously', or 'seamlessly'. "
            "Be grounded only in the completed work below. "
            "Do not say 'completed tasks', 'the task list', 'secondary themes', 'tasks included', or 'system enhancements'.\n\n"
            f"Completed work:\n{_summary_prompt(tasks)}"
        ),
    )
    return str(response.output_text or "").strip()


def refresh_daily_completion_summary(store, ai_client, *, timezone_name: str = "America/Toronto", now: datetime | None = None) -> dict:
    summary_date, tasks = load_completed_today(store, timezone_name=timezone_name, now=now)
    fingerprint = completion_fingerprint(tasks)

    cached = get_cached_daily_summary(store, summary_date=summary_date, fingerprint=fingerprint)
    if cached is not None:
        return {"status": "cached", "summary_date": summary_date, "completed_count": len(tasks), "summary": cached.get("summary") or ""}

    summary = generate_daily_summary(ai_client, tasks)
    payload = {
        "summary_date": summary_date,
        "fingerprint": fingerprint,
        "summary": summary,
        "completed_count": len(tasks),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    store.client.table("daily_completion_summaries").upsert(payload, on_conflict="summary_date").execute()
    return {"status": "updated", **payload}
