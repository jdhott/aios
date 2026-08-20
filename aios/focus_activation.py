from __future__ import annotations

from aios.temporal import serialize_task_datetime

import json
import os
from typing import Any

from aios.task_writing import AI_TASK_TITLE_GUIDANCE

from aios.storage.supabase_store import SupabaseStore


FOCUS_ACTIVATION_SOURCE = "focus_activation"
_ALLOWED_MINUTES = (5, 10, 15)


def _plain_title(task: dict[str, Any]) -> str:
    direct = str(task.get("title") or "").strip()
    if direct:
        return direct

    props = task.get("properties") or {}
    for key in ("Task Name", "Name", "Title"):
        prop = props.get(key) or {}
        parts = prop.get("title") or prop.get("rich_text") or []
        text = "".join(
            str(
                item.get("plain_text")
                or item.get("text", {}).get("content")
                or ""
            )
            for item in parts
            if isinstance(item, dict)
        ).strip()
        if text:
            return text

    return "Untitled task"


def _resolve_supabase_task(
    store: SupabaseStore,
    task: dict[str, Any],
) -> dict[str, Any] | None:
    task_id = str(task.get("id") or "").strip()
    if not task_id:
        return None

    rows = (
        store.client
        .table("tasks")
        .select("id,title,context,project_id,legacy_notion_id,is_open,is_done,is_archived")
        .eq("id", task_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if rows:
        return dict(rows[0])

    rows = (
        store.client
        .table("tasks")
        .select("id,title,context,project_id,legacy_notion_id,is_open,is_done,is_archived")
        .eq("legacy_notion_id", task_id)
        .limit(1)
        .execute()
        .data
        or []
    )

    return dict(rows[0]) if rows else None


def _normalize_minutes(value: Any) -> int:
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        return 10

    return min(
        _ALLOWED_MINUTES,
        key=lambda option: abs(option - minutes),
    )


def list_focus_activation_children(
    store: SupabaseStore,
    parent_task_id: str,
) -> list[dict[str, Any]]:
    rows = (
        store.client
        .table("tasks")
        .select(
            "id,title,is_open,is_done,is_archived,is_just_do_it,"
            "parent_task_id,step_order,generated_source,duration,"
            "activation_disposition,defer_until,"
            "created_at,updated_at,completed_at"
        )
        .eq("parent_task_id", parent_task_id)
        .eq("generated_source", FOCUS_ACTIVATION_SOURCE)
        .order("step_order")
        .execute()
        .data
        or []
    )

    return list(rows)


def complete_open_focus_activation_children(
    store: SupabaseStore,
    parent_task_id: str,
    *,
    completed_at: str,
) -> int:
    """Complete any still-open AIOS-generated activation children for a parent.

    Parent completion makes its generated starting moves obsolete. Preserve the
    child rows as execution history rather than deleting them.
    """
    rows = (
        store.client
        .table("tasks")
        .select("id")
        .eq("parent_task_id", parent_task_id)
        .eq("generated_source", FOCUS_ACTIVATION_SOURCE)
        .eq("is_open", True)
        .eq("is_done", False)
        .eq("is_archived", False)
        .execute()
        .data
        or []
    )

    for row in rows:
        (
            store.client
            .table("tasks")
            .update({
                "is_done": True,
                "is_open": False,
                "completed_at": completed_at,
                "updated_at": completed_at,
            })
            .eq("id", row["id"])
            .execute()
        )

    return len(rows)


def get_active_focus_activation(
    store: SupabaseStore,
    parent_task_id: str,
) -> dict[str, Any] | None:
    rows = (
        store.client
        .table("tasks")
        .select(
            "id,title,is_open,is_done,is_archived,is_just_do_it,"
            "parent_task_id,step_order,generated_source,duration,"
            "activation_disposition,defer_until"
        )
        .eq("parent_task_id", parent_task_id)
        .eq("generated_source", FOCUS_ACTIVATION_SOURCE)
        .eq("is_open", True)
        .eq("is_done", False)
        .eq("is_archived", False)
        # A Start Here marked not useful remains open while context coaching
        # is active so the dashboard can keep showing what the user rejected.
        .order("step_order")
        .limit(1)
        .execute()
        .data
        or []
    )

    return dict(rows[0]) if rows else None


def next_focus_activation_step_order(
    store: SupabaseStore,
    parent_task_id: str,
) -> int:
    rows = list_focus_activation_children(
        store,
        parent_task_id,
    )

    existing_orders = [
        int(row["step_order"])
        for row in rows
        if row.get("step_order") is not None
    ]

    return max(existing_orders, default=0) + 1


def create_focus_activation_child(
    store: SupabaseStore,
    *,
    parent_task_id: str,
    title: str,
    minutes: int = 10,
    context: str | None = None,
) -> dict[str, Any]:
    existing = get_active_focus_activation(
        store,
        parent_task_id,
    )

    if existing:
        return existing

    step_order = next_focus_activation_step_order(
        store,
        parent_task_id,
    )

    minutes = _normalize_minutes(minutes)

    response = (
        store.client
        .table("tasks")
        .insert({
            "legacy_notion_id": None,
            "title": title,
            "context": str(context or "").strip() or None,
            "is_open": True,
            "is_done": False,
            "is_archived": False,
            "is_just_do_it": True,
            "is_quick_win": False,
            "duration": f"{minutes} min",
            "parent_task_id": parent_task_id,
            "step_order": step_order,
            "generated_source": FOCUS_ACTIVATION_SOURCE,
        })
        .execute()
    )

    rows = response.data or []

    if not rows:
        raise RuntimeError(
            "Focus activation child insert returned no row."
        )

    return dict(rows[0])



def mark_focus_activation_not_now(
    store: SupabaseStore,
    task_id: str,
) -> dict[str, Any]:
    rows = (
        store.client
        .table("tasks")
        .select(
            "id,title,generated_source,is_done,is_archived,"
            "activation_disposition"
        )
        .eq("id", task_id)
        .limit(1)
        .execute()
        .data
        or []
    )

    if not rows:
        raise RuntimeError(f"Activation task {task_id} not found.")

    current = dict(rows[0])

    if current.get("generated_source") != FOCUS_ACTIVATION_SOURCE:
        raise RuntimeError(
            "Only focus activation tasks can be marked Not now."
        )

    if current.get("is_done") or current.get("is_archived"):
        raise RuntimeError(
            "Completed or archived activation tasks cannot be marked Not now."
        )

    response = (
        store.client
        .table("tasks")
        .update({
            "activation_disposition": "not_now",
            "is_open": False,
        })
        .eq("id", task_id)
        .execute()
    )

    updated = response.data or []

    if not updated:
        raise RuntimeError(
            "Not-now activation update returned no row."
        )

    return dict(updated[0])


def snooze_focus_activation(
    store: SupabaseStore,
    task_id: str,
    defer_until: str,
) -> dict[str, Any]:
    defer_until = str(defer_until or "").strip()
    if not defer_until:
        raise ValueError("defer_until is required.")
    defer_until = serialize_task_datetime(defer_until)

    rows = (
        store.client
        .table("tasks")
        .select(
            "id,title,generated_source,is_done,is_archived"
        )
        .eq("id", task_id)
        .limit(1)
        .execute()
        .data
        or []
    )

    if not rows:
        raise RuntimeError(f"Activation task {task_id} not found.")

    current = dict(rows[0])

    if current.get("generated_source") != FOCUS_ACTIVATION_SOURCE:
        raise RuntimeError(
            "Only focus activation tasks can be snoozed."
        )

    if current.get("is_done") or current.get("is_archived"):
        raise RuntimeError(
            "Completed or archived activation tasks cannot be snoozed."
        )

    response = (
        store.client
        .table("tasks")
        .update({
            "defer_until": defer_until,
            "is_open": False,
        })
        .eq("id", task_id)
        .execute()
    )

    updated = response.data or []

    if not updated:
        raise RuntimeError(
            "Snooze activation update returned no row."
        )

    return dict(updated[0])

def generate_next_focus_activation(
    client,
    *,
    parent_title: str,
    task_context: str = "",
    project_context: str = "",
    completed_steps: list[str],
    unavailable_steps: list[str] | None = None,
) -> dict[str, Any] | None:
    """
    Generate exactly one next JDI-sized activation step.

    Unlike the older dashboard guidance feature, this creates durable task
    state. If AI generation fails, return None rather than creating a generic
    fallback task.
    """
    if client is None:
        return None

    history = "\n".join(
        f"{index}. {step}"
        for index, step in enumerate(completed_steps, start=1)
    )

    if not history:
        history = "(No activation steps completed yet.)"

    unavailable_steps = [
        str(step).strip()
        for step in (unavailable_steps or [])
        if str(step).strip()
    ]

    unavailable_history = "\n".join(
        f"{index}. {step}"
        for index, step in enumerate(unavailable_steps, start=1)
    )

    if not unavailable_history:
        unavailable_history = "(No unavailable activation steps.)"

    model = os.getenv(
        "AIOS_FOCUS_GUIDANCE_MODEL",
        "gpt-4.1-mini",
    )

    prompt = f"""You are helping a person make progress on ONE already-selected priority task.

Parent task:
{parent_title}

Authoritative Task Context:
{task_context or "(none)"}

Relevant Project Context:
{project_context or "(none)"}

Previously completed activation steps:
{history}

Unavailable / rejected activation steps:
{unavailable_history}

Generate exactly ONE next small action.

Return JSON only with exactly:
{{"title":"...","context":"...","minutes":10}}

Rules:
- The action must advance the parent task.
- Treat Task Context as authoritative; never contradict it.
- Use Project Context when relevant, but prefer more-specific Task Context.
- Do not repeat or substantially duplicate any completed or unavailable activation step.
- The action must be executable now and must not depend on waiting for a reply, delivery, approval, future date, or external event.
- It must be a concrete action the person can do now.
- Treat it as a Just Do It task: small, low-friction, and immediately executable.
- Prefer an action that can be completed in 5 to 15 minutes.
- Do not generate a plan or checklist containing multiple actions.
- Do not merely say "continue", "work on it", "get started", or "break it down".
- Do not invent people, deadlines, places, preferences, tools, or facts not provided.
- Choose minutes from 5, 10, or 15.
- Context is optional supporting detail. Keep it to one short sentence and leave it empty when it adds nothing beyond the title.
- Do not repeat the parent task in context merely to make the child understandable; the UI already shows the relationship.

{AI_TASK_TITLE_GUIDANCE}
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

        title = str(data.get("title") or "").strip()
        if not title:
            return None

        # Basic duplicate guard in addition to the prompt.
        normalized_title = " ".join(title.lower().split())
        normalized_history = {
            " ".join(step.lower().split())
            for step in (completed_steps + unavailable_steps)
        }

        if normalized_title in normalized_history:
            print(
                "[Focus Activation] AI returned an already-completed step; "
                "no child created."
            )
            return None

        return {
            "title": title[:300],
            "context": str(data.get("context") or "").strip() or None,
            "minutes": _normalize_minutes(data.get("minutes")),
        }

    except Exception as exc:
        print(
            f"[Focus Activation] AI generation failed: {exc}"
        )
        return None


def ensure_next_focus_activation(
    store: SupabaseStore,
    client,
    execution_task: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Ensure the current BNA has exactly one active activation child.

    If an active child already exists, reuse it.
    Otherwise generate the next child using completed activation history.
    """
    resolved = _resolve_supabase_task(
        store,
        execution_task,
    )

    if not resolved:
        print(
            "[Focus Activation] Could not resolve current BNA "
            "to Supabase task."
        )
        return None

    if (
        not resolved.get("is_open", True)
        or resolved.get("is_done")
        or resolved.get("is_archived")
    ):
        return None

    parent_task_id = str(resolved["id"])

    # Context coaching owns the next-step decision while it is active. Do not
    # blindly generate another Start Here until the user saves the draft.
    coaching_rows = (store.client.table("tasks").select("focus_context_help_state").eq("id", parent_task_id).limit(1).execute().data or [])
    coaching_state = str((coaching_rows[0] if coaching_rows else {}).get("focus_context_help_state") or "")
    if coaching_state in {"pending", "answer_pending", "ready"}:
        print(f"[Focus Activation] Waiting for context coaching on: {parent_task_id}")
        return None

    parent_title = str(
        resolved.get("title")
        or _plain_title(execution_task)
    ).strip()

    existing = get_active_focus_activation(
        store,
        parent_task_id,
    )

    if existing:
        print(
            f"[Focus Activation] Reusing active step "
            f"{existing.get('step_order')} for: {parent_title}"
        )
        return existing

    history = list_focus_activation_children(
        store,
        parent_task_id,
    )

    completed_steps = [
        str(row.get("title") or "").strip()
        for row in history
        if row.get("is_done")
        and not row.get("is_archived")
        and str(row.get("title") or "").strip()
    ]

    unavailable_steps = [
        str(row.get("title") or "").strip()
        for row in history
        if not row.get("is_done")
        and not row.get("is_archived")
        and (
            row.get("activation_disposition") in {"not_now", "not_useful"}
            or row.get("defer_until")
        )
        and str(row.get("title") or "").strip()
    ]

    task_context = str(resolved.get("context") or "").strip()
    project_context = ""
    project_id = str(resolved.get("project_id") or "").strip()
    if project_id:
        try:
            project_rows = (store.client.table("projects").select("context").eq("id", project_id).limit(1).execute().data or [])
            if project_rows:
                project_context = str(project_rows[0].get("context") or "").strip()
        except Exception as exc:
            print(f"[Focus Activation] Project context lookup failed: {exc}")

    generated = generate_next_focus_activation(
        client,
        parent_title=parent_title,
        task_context=task_context,
        project_context=project_context,
        completed_steps=completed_steps,
        unavailable_steps=unavailable_steps,
    )

    if not generated:
        print(
            f"[Focus Activation] No new activation step generated for: "
            f"{parent_title}"
        )
        return None

    child = create_focus_activation_child(
        store,
        parent_task_id=parent_task_id,
        title=generated["title"],
        minutes=generated["minutes"],
        context=generated.get("context"),
    )

    print(
        f"[Focus Activation] Created step "
        f"{child.get('step_order')} "
        f"({generated['minutes']} min) for: {parent_title}"
    )

    return child
