from dataclasses import replace

from aios.review.models import InboxReview
from aios.services.review_service import ReviewService


class FakeReviewRepo:
    def __init__(self):
        self.review = InboxReview(
            id="r1",
            inbox_item_id="i1",
            review_type="possible_duplicate",
            state="pending",
            payload={
                "candidate_task_id": "t1",
                "candidate_task_title": "Existing task",
            },
            decision=None,
            created_at=None,
            updated_at=None,
            resolved_at=None,
        )

    def get_review(self, review_id):
        assert review_id == "r1"
        return self.review

    def get_reviews_for_item(self, inbox_item_id):
        assert inbox_item_id == "i1"
        return [self.review]

    def update_state(self, review_id, state, *, payload=None):
        assert review_id == "r1"
        assert state == "pending"

        self.review = replace(
            self.review,
            state=state,
            payload=payload or {},
        )

        return self.review


class FakeInboxRepo:
    def get_row(self, inbox_item_id):
        assert inbox_item_id == "i1"
        return {
            "id": "i1",
            "text": "Create a new task anyway",
        }


service = ReviewService(
    review_repository=FakeReviewRepo(),
    inbox_repository=FakeInboxRepo(),
)

result = service.request_possible_duplicate_create_anyway(
    "r1"
)

assert result.state == "pending"
assert (
    result.payload["requested_action"]
    == "create_anyway"
)

assert (
    result.payload["candidate_task_id"]
    == "t1"
)

print("Create-anyway request keeps review pending: PASS")
print("Requested action persisted in payload: PASS")
print("Existing review payload preserved: PASS")
print(
    "RESULT: POSSIBLE DUPLICATE CREATE-ANYWAY "
    "REQUEST V1 PASSED"
)
