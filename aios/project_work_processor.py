from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from aios.focus_activation import list_focus_activation_children
from aios.project_work import generate_project_work, summarize_project_work_answer
from aios.project_work_proposals import (
    list_project_work_feedback,
    replace_project_work_proposals,
)
from aios.storage.supabase_store import SupabaseStore


MANUAL_STATE_PENDING = "pending"
MANUAL_STATE_ACTIONABLE = "actionable"
MANUAL_STATE_WAITING = "waiting"
MANUAL_STATE_FAILED = "failed"
MANUAL_STATE_CLARIFICATION = "clarification"
MANUAL_STATE_ANSWER_PENDING = "answer_pending"
MANUAL_STATE_CONTEXT_REVIEW = "context_review"


def _manual_generation_requested(project: dict[str, Any]) -> bool:
    return (
        str(project.get("work_generation_state") or "").strip().lower()
        == MANUAL_STATE_PENDING
        and bool(str(project.get("work_generation_requested_at") or "").strip())
    )


def _finish_manual_generation(
    store: SupabaseStore,
    project_id: str,
    state: str,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    (
        store.client
        .table("projects")
        .update({
            "work_generation_state": state,
            "work_generation_completed_at": now,
        })
        .eq("id", project_id)
        .execute()
    )


def refresh_project_work_proposals(
    store: SupabaseStore,
    client,
) -> list[dict[str, Any]]:
    """
    Refresh review-only project-work proposals.

    Automatic generation remains intentionally conservative:
      - active projects only
      - project must have an explicit Outcome or legacy project_anchor
      - project must currently have no normal open executable project work

    A manual generation request is different: it deliberately bypasses only
    the "no open work" gate so AIOS can audit one project for genuinely
    missing work while still receiving all existing open/completed work as
    grounding context.

    This function creates proposals only, never real tasks.
    """

    projects = (
        store.client
        .table("projects")
        .select(
            "id,name,status,is_active,outcome,context,"
            "work_generation_requested_at,work_generation_completed_at,"
            "work_generation_state,work_generation_question,work_generation_answer,"
            "work_generation_context_update,work_generation_round"
        )
        .eq("is_active", True)
        .execute()
        .data
        or []
    )

    results: list[dict[str, Any]] = []

    for project in projects:
        project_id = str(project.get("id") or "").strip()
        project_name = str(project.get("name") or "").strip()
        manual_requested = _manual_generation_requested(project)

        if not project_id or not project_name:
            continue

        generation_state = str(project.get("work_generation_state") or "").strip().lower()
        if generation_state == MANUAL_STATE_ANSWER_PENDING:
            summary = summarize_project_work_answer(
                client,
                project_context=str(project.get("context") or ""),
                question=str(project.get("work_generation_question") or ""),
                answer=str(project.get("work_generation_answer") or ""),
            )
            if summary:
                (store.client.table("projects").update({
                    "work_generation_context_update": summary,
                    "work_generation_state": MANUAL_STATE_CONTEXT_REVIEW,
                    "work_generation_completed_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", project_id).execute())
                results.append({"project_id": project_id, "project_name": project_name, "state": MANUAL_STATE_CONTEXT_REVIEW, "proposals": [], "manual": True})
            else:
                _finish_manual_generation(store, project_id, MANUAL_STATE_FAILED)
            continue

        task_rows = (
            store.client
            .table("tasks")
            .select(
                "id,title,project_id,task_role,generated_source,"
                "is_open,is_done,is_archived,parent_task_id,"
                "activation_disposition,defer_until"
            )
            .eq("project_id", project_id)
            .execute()
            .data
            or []
        )

        anchors = [
            row
            for row in task_rows
            if row.get("task_role") == "project_anchor"
            and not row.get("is_archived")
        ]

        project_outcome = str(project.get("outcome") or "").strip()
        anchor = anchors[0] if anchors else None
        anchor_id = str(anchor.get("id") or "") if anchor else ""
        anchor_title = (
            str(anchor.get("title") or "").strip()
            if anchor
            else ""
        )

        if not project_outcome and not anchor_title:
            if manual_requested:
                _finish_manual_generation(
                    store,
                    project_id,
                    MANUAL_STATE_FAILED,
                )
                results.append({
                    "project_id": project_id,
                    "project_name": project_name,
                    "state": MANUAL_STATE_FAILED,
                    "proposals": [],
                    "manual": True,
                })
            continue

        open_work = [
            str(row.get("title") or "").strip()
            for row in task_rows
            if row.get("is_open")
            and not row.get("is_done")
            and not row.get("is_archived")
            and row.get("task_role") != "project_anchor"
            and row.get("generated_source") != "focus_activation"
            and str(row.get("title") or "").strip()
        ]

        # Automatic generation is a gap-filler. Manual generation is an
        # explicit audit for missing work and therefore bypasses this one gate.
        if open_work and not manual_requested:
            continue

        completed_work = [
            str(row.get("title") or "").strip()
            for row in task_rows
            if row.get("is_done")
            and not row.get("is_archived")
            and row.get("task_role") != "project_anchor"
            and row.get("generated_source") != "focus_activation"
            and str(row.get("title") or "").strip()
        ]

        activation_history = (
            list_focus_activation_children(store, anchor_id)
            if anchor_id
            else []
        )

        completed_activation_steps = [
            str(row.get("title") or "").strip()
            for row in activation_history
            if row.get("is_done")
            and not row.get("is_archived")
            and str(row.get("title") or "").strip()
        ]

        proposal_feedback = list_project_work_feedback(
            store,
            project_id,
            limit=5,
        )

        generated = generate_project_work(
            client,
            project_name=project_name,
            project_outcome=project_outcome,
            project_context=str(project.get("context") or ""),
            project_anchor_title=anchor_title,
            completed_work=completed_work,
            open_work=open_work,
            completed_activation_steps=completed_activation_steps,
            proposal_feedback=proposal_feedback,
            clarification_round=int(project.get("work_generation_round") or 0),
            allow_clarification=manual_requested,
        )

        titles: list[str] = []
        generated_state = (
            str(generated.get("state") or "").strip().lower()
            if generated
            else MANUAL_STATE_FAILED
        )

        if generated_state == MANUAL_STATE_CLARIFICATION and manual_requested:
            question = str(generated.get("question") or "").strip()
            if question:
                next_round = int(project.get("work_generation_round") or 0) + 1
                (store.client.table("projects").update({
                    "work_generation_state": MANUAL_STATE_CLARIFICATION,
                    "work_generation_question": question,
                    "work_generation_answer": None,
                    "work_generation_context_update": None,
                    "work_generation_round": next_round,
                    "work_generation_completed_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", project_id).execute())
                results.append({"project_id": project_id, "project_name": project_name, "state": MANUAL_STATE_CLARIFICATION, "proposals": [], "manual": True})
                continue
            generated_state = MANUAL_STATE_WAITING

        if generated_state == MANUAL_STATE_ACTIONABLE:
            titles = [
                str(item.get("title") or "").strip()
                for item in (generated.get("tasks") or [])
                if str(item.get("title") or "").strip()
            ]
            if not titles:
                generated_state = MANUAL_STATE_WAITING
        elif generated_state != MANUAL_STATE_WAITING:
            generated_state = MANUAL_STATE_FAILED

        proposals = replace_project_work_proposals(
            store,
            project_id=project_id,
            titles=titles,
        )

        if manual_requested:
            _finish_manual_generation(
                store,
                project_id,
                generated_state,
            )

        print(
            "[Project Work] "
            f"{project_name}: "
            f"{len(proposals)} proposal(s)"
            + (" [manual]" if manual_requested else "")
        )

        results.append({
            "project_id": project_id,
            "project_name": project_name,
            "state": generated_state,
            "proposals": proposals,
            "manual": manual_requested,
        })

    return results
