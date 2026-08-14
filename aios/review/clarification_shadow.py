from __future__ import annotations

from typing import Any

from aios.ingestion.models import InboxItem


def shadow_clarification_review(
    *,
    inbox_repo,
    review_repo,
    item: InboxItem,
    first_page: dict[str, Any],
    task_title: str,
    original_title: str,
    suggestions: list[str],
    clarification_mode: str,
    clarification_reason: str,
):
    """Create/reuse a shadow clarification review for the original inbox item."""
    shadow_row = inbox_repo.get_or_create_shadow_item(item)

    open_reviews = review_repo.get_open_reviews_for_item(
        str(shadow_row["id"])
    )

    for review in open_reviews:
        if review.review_type == "clarification":
            return review, False

    proposed_text = (
        suggestions[0].strip()
        if suggestions and suggestions[0].strip()
        else original_title.strip()
    )

    payload = {
        "original_text": original_title,
        "proposed_text": proposed_text,
        "clarification_mode": clarification_mode,
        "clarification_reason": clarification_reason,
        "notion_task_page_id": first_page.get("id"),
        "task_title": task_title,
        "authority": "notion_shadow_only",
    }

    review = review_repo.create_review(
        inbox_item_id=str(shadow_row["id"]),
        review_type="clarification",
        state="pending",
        payload=payload,
    )

    return review, True
