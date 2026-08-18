from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from zoneinfo import ZoneInfo

SUMMARY_MODEL = "gpt-4.1-mini"
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
    return sha256("\n".join(parts).encode("utf-8")).hexdigest()


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
            store.client.table("projects").select("id,title").in_("id", project_ids).execute().data or []
        )
        project_titles = {
            str(row.get("id")): str(row.get("title") or "").strip()
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
            "Summarize the flavour and main focus of today's completed work in 1-2 short sentences. "
            "Use only the completed tasks below. Group related work or projects when useful. "
            "Be concrete and reflective, not congratulatory or judgmental. Do not say the day was productive, successful, busy, or good. "
            "Do not invent motives, emotions, priorities, or accomplishments beyond the task titles and their project/parent context. "
            "Prefer a natural sentence such as 'Today was mostly about...' or 'The day's completed work focused on...'.\n\n"
            f"Completed tasks:\n{_summary_prompt(tasks)}"
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
