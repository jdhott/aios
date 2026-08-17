#!/usr/bin/env python3
from aios.ingestion.models import InboxItem
from aios.review.clarification_shadow import create_clarification_review
from aios.review.models import InboxReview

item = InboxItem(
    text="Plan canning",
    notes=[],
    source="notion",
    source_item_id="notion-block-clarify-123",
    source_container_id="brain-dump-sync",
    source_type="paragraph",
)


class FakeInboxRepo:
    def get_review_row_for_item(self, got):
        assert got.source_item_id == "notion-block-clarify-123"
        return {"id": "supabase-inbox-clarify-1"}


class FakeReviewRepo:
    def __init__(self):
        self.open = []
        self.created = []

    def get_open_reviews_for_item(self, inbox_id):
        assert inbox_id == "supabase-inbox-clarify-1"
        return list(self.open)

    def create_review(self, **kwargs):
        self.created.append(kwargs)
        review = InboxReview(
            id="review-clarify-1",
            inbox_item_id=kwargs["inbox_item_id"],
            review_type=kwargs["review_type"],
            state=kwargs["state"],
            payload=kwargs["payload"],
        )
        self.open.append(review)
        return review


inbox_repo = FakeInboxRepo()
review_repo = FakeReviewRepo()

kwargs = dict(
    inbox_repo=inbox_repo,
    review_repo=review_repo,
    item=item,
    task_id="supabase-task-clarify-1",
    task_title="Clarify next action: Plan canning",
    original_title="Plan canning",
    suggestions=["List the foods to preserve by canning this year"],
    clarification_mode="procedural",
    clarification_reason="default_procedural",
)

first, first_created = create_clarification_review(**kwargs)
second, second_created = create_clarification_review(**kwargs)

if not first_created:
    raise RuntimeError("First clarification review should be created.")
if second_created:
    raise RuntimeError("Second call should reuse existing review.")
if first.id != second.id:
    raise RuntimeError("Repeated creation returned a different review.")
if len(review_repo.created) != 1:
    raise RuntimeError("Expected exactly one review creation.")

payload = review_repo.created[0]["payload"]
expected = {
    "original_text": "Plan canning",
    "proposed_text": "List the foods to preserve by canning this year",
    "task_id": "supabase-task-clarify-1",
    "task_title": "Clarify next action: Plan canning",
    "clarification_mode": "procedural",
    "clarification_reason": "default_procedural",
    "authority": "supabase-clarification-review-v1",
}

for key, value in expected.items():
    if payload.get(key) != value:
        raise RuntimeError(f"Payload mismatch for {key}: {payload.get(key)!r}")

print("Source-neutral inbox identity: PASS")
print("Authoritative Supabase task identity: PASS")
print("Clarification proposal payload: PASS")
print("Pending clarification review creation: PASS")
print("Open-review idempotency: PASS")
print("Supabase clarification authority marker: PASS")
print("RESULT: CLARIFICATION REVIEW AUTHORITY SMOKE TEST PASSED")
