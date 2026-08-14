#!/usr/bin/env python3
from datetime import datetime, timezone

from aios.review.models import InboxReview
from aios.services.review_service import ReviewService


class FakeReviewRepository:
    def __init__(self):
        self.reviews = [
            InboxReview(
                id="clarify-1",
                inbox_item_id="inbox-1",
                review_type="clarification",
                state="pending_confirmation",
                payload={
                    "original_text": "Plan canning",
                    "proposed_text": "List foods to can this year",
                },
                created_at=datetime.now(timezone.utc),
            ),
            InboxReview(
                id="duplicate-1",
                inbox_item_id="inbox-2",
                review_type="possible_duplicate",
                state="pending",
                payload={
                    "candidate_task_title": "Review generator quote",
                    "score": 0.82,
                },
                created_at=datetime.now(timezone.utc),
            ),
        ]

    def get_open_reviews(self):
        return list(self.reviews)

    def get_review(self, review_id):
        return next(
            (r for r in self.reviews if r.id == review_id),
            None,
        )


class FakeInboxRepository:
    rows = {
        "inbox-1": {
            "id": "inbox-1",
            "text": "Plan canning",
            "clean_text": "Plan canning",
        },
        "inbox-2": {
            "id": "inbox-2",
            "text": "Check generator quote",
            "clean_text": "Check generator quote",
        },
    }

    def get_row(self, inbox_id):
        return self.rows.get(inbox_id)


service = ReviewService(
    review_repository=FakeReviewRepository(),
    inbox_repository=FakeInboxRepository(),
)

queue = service.list_pending_reviews()
assert len(queue) == 2

assert queue[0].review_type == "clarification"
assert queue[0].subject_text == "Plan canning"
assert queue[0].options == ["List foods to can this year"]

assert queue[1].review_type == "possible_duplicate"
assert queue[1].subject_text == "Check generator quote"
assert queue[1].options == [
    "link_existing",
    "create_anyway",
    "ignore",
]

single = service.get_review("duplicate-1")
assert single is not None
assert single.id == "duplicate-1"

filtered = service.list_pending_reviews(
    review_types=["clarification"],
)
assert len(filtered) == 1

assert isinstance(queue[1].to_dict()["created_at"], str)

print("Unified open review queue: PASS")
print("Clarification payload normalization: PASS")
print("Possible duplicate option normalization: PASS")
print("Single review lookup: PASS")
print("Review type filtering: PASS")
print("JSON-safe representation: PASS")
print("RESULT: APP REVIEW READ SERVICE PHASE 2.1 SMOKE TEST PASSED")
