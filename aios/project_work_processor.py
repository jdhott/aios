from __future__ import annotations

from typing import Any

from aios.focus_activation import (
    list_focus_activation_children,
)
from aios.project_work import generate_project_work
from aios.project_work_proposals import (
    list_project_work_feedback,
    replace_project_work_proposals,
)
from aios.storage.supabase_store import SupabaseStore


def refresh_project_work_proposals(
    store: SupabaseStore,
    client,
) -> list[dict[str, Any]]:
    """
    Refresh review-only project-work proposals.

    V1 scope is intentionally conservative:
      - active projects only
      - project must have a project_anchor task
      - project must currently have no normal open executable project work
      - AI output is grounded/validated by generate_project_work()
      - this function creates proposals only, never real tasks
    """

    projects = (
        store.client
        .table("projects")
        .select("id,name,status,is_active,context")
        .eq("is_active", True)
        .execute()
        .data
        or []
    )

    results: list[dict[str, Any]] = []

    for project in projects:
        project_id = str(project.get("id") or "").strip()
        project_name = str(project.get("name") or "").strip()

        if not project_id or not project_name:
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

        if not anchors:
            continue

        # V1 assumes one canonical project anchor.
        anchor = anchors[0]
        anchor_id = str(anchor.get("id") or "")
        anchor_title = str(anchor.get("title") or "").strip()

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

        # If the project already has real executable work, normal execution
        # should handle it. Do not manufacture more project work.
        if open_work:
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
            list_focus_activation_children(
                store,
                anchor_id,
            )
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
            project_context=str(
                project.get("context") or ""
            ),
            project_anchor_title=anchor_title,
            completed_work=completed_work,
            open_work=open_work,
            completed_activation_steps=completed_activation_steps,
            proposal_feedback=proposal_feedback,
        )

        titles: list[str] = []

        if generated and generated.get("state") == "actionable":
            titles = [
                str(item.get("title") or "").strip()
                for item in (generated.get("tasks") or [])
                if str(item.get("title") or "").strip()
            ]

        proposals = replace_project_work_proposals(
            store,
            project_id=project_id,
            titles=titles,
        )

        print(
            "[Project Work] "
            f"{project_name}: "
            f"{len(proposals)} proposal(s)"
        )

        results.append({
            "project_id": project_id,
            "project_name": project_name,
            "state": (
                generated.get("state")
                if generated
                else "failed"
            ),
            "proposals": proposals,
        })

    return results
