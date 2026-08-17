from __future__ import annotations

from typing import Any

from aios.ingestion.models import InboxItem


CLARIFICATION_REVIEW_AUTHORITY_VERSION = (
    "supabase-clarification-review-v1"
)


def create_clarification_review(
    *,
    inbox_repo,
    review_repo,
    item: InboxItem,
    task_id: str,
    task_title: str,
    original_title: str,
    suggestions: list[str],
    clarification_mode: str,
    clarification_reason: str,
):
    """Create/reuse the authoritative Supabase clarification review."""

    review_row = inbox_repo.get_review_row_for_item(
        item
    )

    open_reviews = (
        review_repo.get_open_reviews_for_item(
            str(review_row["id"])
        )
    )

    for review in open_reviews:
        if review.review_type == "clarification":
            return review, False

    proposed_text = (
        suggestions[0].strip()
        if suggestions
        and suggestions[0].strip()
        else original_title.strip()
    )

    payload: dict[str, Any] = {
        "original_text": original_title,
        "proposed_text": proposed_text,
        "task_id": str(task_id),
        "task_title": task_title,
        "clarification_mode":
            clarification_mode,
        "clarification_reason":
            clarification_reason,
        "authority":
            CLARIFICATION_REVIEW_AUTHORITY_VERSION,
    }

    review = review_repo.create_review(
        inbox_item_id=str(review_row["id"]),
        review_type="clarification",
        state="pending",
        payload=payload,
    )

    return review, True
