#!/usr/bin/env python3
from aios.review.models import InboxReview
from aios.review.clarification_transitions import (
    mark_clarification_awaiting_answer,
    mark_clarification_pending_confirmation,
    resolve_clarification_review,
)

class FakeRepo:
    def __init__(self):
        self.current = InboxReview(
            id="review-1",
            inbox_item_id="inbox-1",
            review_type="clarification",
            state="pending",
            payload={
                "original_text": "Plan canning",
                "proposed_text": "List foods to preserve",
                "authority": "notion_shadow_only",
            },
        )

    def update_state(self, review_id, state, *, payload=None):
        assert review_id == self.current.id
        self.current = InboxReview(
            id=self.current.id,
            inbox_item_id=self.current.inbox_item_id,
            review_type=self.current.review_type,
            state=state,
            payload=payload or {},
            decision=self.current.decision,
        )
        return self.current

    def resolve_review(self, review_id, *, decision):
        assert review_id == self.current.id
        self.current = InboxReview(
            id=self.current.id,
            inbox_item_id=self.current.inbox_item_id,
            review_type=self.current.review_type,
            state="resolved",
            payload=self.current.payload,
            decision=decision,
        )
        return self.current

repo = FakeRepo()

awaiting = mark_clarification_awaiting_answer(
    review_repo=repo,
    review=repo.current,
    question="Which foods do you want to preserve?",
)
assert awaiting.state == "awaiting_answer"
assert awaiting.payload["question"] == "Which foods do you want to preserve?"
assert awaiting.payload["original_text"] == "Plan canning"
print("pending → awaiting_answer: PASS")

pending_confirmation = mark_clarification_pending_confirmation(
    review_repo=repo,
    review=repo.current,
    answer="Tomatoes and peaches",
    proposed_text="List tomatoes and peaches to preserve this year",
)
assert pending_confirmation.state == "pending_confirmation"
assert pending_confirmation.payload["answer"] == "Tomatoes and peaches"
assert pending_confirmation.payload["question"] == "Which foods do you want to preserve?"
assert pending_confirmation.payload["proposed_text"] == "List tomatoes and peaches to preserve this year"
print("awaiting_answer → pending_confirmation: PASS")

resolved = resolve_clarification_review(
    review_repo=repo,
    review=repo.current,
    selected_text="List tomatoes and peaches to preserve this year",
    accepted_text="List tomatoes and peaches to preserve this year",
)
assert resolved.state == "resolved"
assert resolved.decision["action"] == "accept_clarification"
assert resolved.decision["accepted_text"] == "List tomatoes and peaches to preserve this year"
assert resolved.decision["selected_text"] == "List tomatoes and peaches to preserve this year"
print("pending_confirmation → resolved: PASS")

print("RESULT: CLARIFICATION REVIEW STATE TRANSITIONS SMOKE TEST PASSED")
