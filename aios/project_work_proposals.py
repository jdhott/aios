from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from aios.storage.supabase_store import SupabaseStore


PROPOSAL_STATUS_PROPOSED = "proposed"
PROPOSAL_STATUS_ACCEPTED = "accepted"
PROPOSAL_STATUS_DISMISSED = "dismissed"


def _normalized_title(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def list_proposed_project_work(
    store: SupabaseStore,
    project_id: str,
) -> list[dict[str, Any]]:
    rows = (
        store.client
        .table("project_work_proposals")
        .select(
            "id,project_id,title,status,feedback,"
            "created_at,updated_at,accepted_at,dismissed_at"
        )
        .eq("project_id", project_id)
        .eq("status", PROPOSAL_STATUS_PROPOSED)
        .order("created_at")
        .execute()
        .data
        or []
    )

    return [dict(row) for row in rows]


def replace_project_work_proposals(
    store: SupabaseStore,
    *,
    project_id: str,
    titles: list[str],
) -> list[dict[str, Any]]:
    """
    Synchronize the current proposed work for one project.

    - unchanged proposed titles are preserved
    - stale proposed titles are dismissed
    - new validated titles are inserted
    """
    project_id = str(project_id or "").strip()
    if not project_id:
        raise ValueError("project_id is required.")

    clean_titles: list[str] = []
    seen: set[str] = set()

    for value in titles or []:
        title = str(value or "").strip()
        key = _normalized_title(title)

        if not title or not key or key in seen:
            continue

        seen.add(key)
        clean_titles.append(title)

    existing = list_proposed_project_work(
        store,
        project_id,
    )

    existing_by_key = {
        _normalized_title(row.get("title") or ""): row
        for row in existing
    }

    desired_keys = {
        _normalized_title(title)
        for title in clean_titles
    }

    now = datetime.now(timezone.utc).isoformat()

    # Dismiss proposals no longer present in the validated result.
    for key, row in existing_by_key.items():
        if key in desired_keys:
            continue

        (
            store.client
            .table("project_work_proposals")
            .update({
                "status": PROPOSAL_STATUS_DISMISSED,
                "dismissed_at": now,
                "updated_at": now,
            })
            .eq("id", row["id"])
            .eq("status", PROPOSAL_STATUS_PROPOSED)
            .execute()
        )

    # Insert genuinely new proposals.
    for title in clean_titles:
        key = _normalized_title(title)

        if key in existing_by_key:
            continue

        response = (
            store.client
            .table("project_work_proposals")
            .insert({
                "project_id": project_id,
                "title": title,
                "status": PROPOSAL_STATUS_PROPOSED,
            })
            .execute()
        )

        if not (response.data or []):
            raise RuntimeError(
                "Project-work proposal insert returned no row."
            )

    return list_proposed_project_work(
        store,
        project_id,
    )


def accept_project_work_proposal(
    store: SupabaseStore,
    proposal_id: str,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()

    response = (
        store.client
        .table("project_work_proposals")
        .update({
            "status": PROPOSAL_STATUS_ACCEPTED,
            "accepted_at": now,
            "updated_at": now,
        })
        .eq("id", proposal_id)
        .eq("status", PROPOSAL_STATUS_PROPOSED)
        .execute()
    )

    rows = response.data or []

    if not rows:
        raise RuntimeError(
            "Proposed project work was not found or is no longer pending."
        )

    return dict(rows[0])


def dismiss_project_work_proposal(
    store: SupabaseStore,
    proposal_id: str,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()

    response = (
        store.client
        .table("project_work_proposals")
        .update({
            "status": PROPOSAL_STATUS_DISMISSED,
            "dismissed_at": now,
            "updated_at": now,
        })
        .eq("id", proposal_id)
        .eq("status", PROPOSAL_STATUS_PROPOSED)
        .execute()
    )

    rows = response.data or []

    if not rows:
        raise RuntimeError(
            "Proposed project work was not found or is no longer pending."
        )

    return dict(rows[0])


def retry_project_work_proposal(
    store: SupabaseStore,
    proposal_id: str,
    *,
    feedback: str,
) -> dict[str, Any]:
    """
    Reject a proposed task with guidance for the next generation attempt.

    We deliberately reuse the existing dismissed lifecycle:
      dismissed + feedback = rejected with guidance
      dismissed + no feedback = ordinary dismissal
    """
    feedback = str(feedback or "").strip()

    if not feedback:
        raise ValueError(
            "Feedback is required when asking AIOS to try again."
        )

    now = datetime.now(timezone.utc).isoformat()

    response = (
        store.client
        .table("project_work_proposals")
        .update({
            "status": PROPOSAL_STATUS_DISMISSED,
            "feedback": feedback,
            "dismissed_at": now,
            "updated_at": now,
        })
        .eq("id", proposal_id)
        .eq("status", PROPOSAL_STATUS_PROPOSED)
        .execute()
    )

    rows = response.data or []

    if not rows:
        raise RuntimeError(
            "Proposed project work was not found or is no longer pending."
        )

    return dict(rows[0])


def list_project_work_feedback(
    store: SupabaseStore,
    project_id: str,
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Return recent rejected proposals that contain user feedback.

    This is proposal-specific guidance, not durable Project Context.
    """
    rows = (
        store.client
        .table("project_work_proposals")
        .select(
            "id,project_id,title,status,feedback,"
            "created_at,updated_at,dismissed_at"
        )
        .eq("project_id", project_id)
        .eq("status", PROPOSAL_STATUS_DISMISSED)
        .order("dismissed_at", desc=True)
        .limit(max(1, min(int(limit), 20)))
        .execute()
        .data
        or []
    )

    return [
        dict(row)
        for row in rows
        if str(row.get("feedback") or "").strip()
    ]
