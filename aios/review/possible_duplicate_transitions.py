from __future__ import annotations
from typing import Any
from aios.review.models import InboxReview

POSSIBLE_DUPLICATE_ACTIONS = {
    "link_existing",
    "create_anyway",
    "ignore",
    "reevaluated_distinct",
}

def refresh_possible_duplicate_payload(
    existing_payload: dict[str, Any] | None,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Merge a fresh duplicate judgment without losing a human create request."""
    payload = dict(existing_payload or {})
    requested_action = str(payload.get("requested_action") or "").strip()
    payload.update(dict(updates or {}))

    if requested_action == "reevaluate":
        payload.pop("requested_action", None)
    elif requested_action:
        payload["requested_action"] = requested_action

    return payload


def resolve_possible_duplicate_review(*, review_repo, review: InboxReview, action: str, candidate_task_id: str | None = None, candidate_task_title: str | None = None, created_task_ids: list[str] | None = None) -> InboxReview:
    if review.review_type != "possible_duplicate":
        raise ValueError(f"Expected possible_duplicate review, got {review.review_type!r}")
    if review.state == "resolved":
        return review
    if review.state != "pending":
        raise ValueError(f"Possible duplicate review must be pending, got {review.state!r}")
    if action not in POSSIBLE_DUPLICATE_ACTIONS:
        raise ValueError(f"Unsupported possible duplicate action: {action!r}")
    decision: dict[str, Any] = {"action": action}
    if candidate_task_id:
        decision["candidate_task_id"] = str(candidate_task_id)
    if candidate_task_title:
        decision["candidate_task_title"] = str(candidate_task_title)
    if created_task_ids:
        decision["created_task_ids"] = [str(x) for x in created_task_ids if x]
    return review_repo.resolve_review(review.id, decision=decision)
