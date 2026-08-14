from __future__ import annotations

from typing import Any

from aios.review.models import InboxReview


def _merge_payload(review: InboxReview, **updates: Any) -> dict[str, Any]:
    payload = dict(review.payload or {})
    for key, value in updates.items():
        if value is not None:
            payload[key] = value
    return payload


def mark_clarification_awaiting_answer(
    *,
    review_repo,
    review: InboxReview,
    question: str,
) -> InboxReview:
    return review_repo.update_state(
        review.id,
        "awaiting_answer",
        payload=_merge_payload(review, question=question),
    )


def mark_clarification_pending_confirmation(
    *,
    review_repo,
    review: InboxReview,
    answer: str,
    proposed_text: str,
) -> InboxReview:
    return review_repo.update_state(
        review.id,
        "pending_confirmation",
        payload=_merge_payload(
            review,
            answer=answer,
            proposed_text=proposed_text,
        ),
    )


def resolve_clarification_review(
    *,
    review_repo,
    review: InboxReview,
    selected_text: str,
    accepted_text: str,
) -> InboxReview:
    return review_repo.resolve_review(
        review.id,
        decision={
            "action": "accept_clarification",
            "selected_text": selected_text,
            "accepted_text": accepted_text,
        },
    )
