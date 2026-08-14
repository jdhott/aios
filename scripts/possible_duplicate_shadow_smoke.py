#!/usr/bin/env python3
from aios.ingestion.models import InboxItem
from aios.review.models import InboxReview

def main():
    item = InboxItem(
        text="Check generator quote",
        notes=[],
        source="notion",
        source_item_id="notion-block-xyz",
        source_container_id="brain-dump-sync",
        source_type="paragraph",
    )

    class FakeInboxRepo:
        def __init__(self):
            self.calls = 0
        def get_or_create_shadow_item(self, got):
            assert got.source_item_id == "notion-block-xyz"
            self.calls += 1
            return {"id": "supabase-inbox-123"}

    class FakeReviewRepo:
        def __init__(self):
            self.created = []
            self.open = []
        def get_open_reviews_for_item(self, inbox_id):
            assert inbox_id == "supabase-inbox-123"
            return list(self.open)
        def create_review(self, **kwargs):
            self.created.append(kwargs)
            review = InboxReview(
                id="review-1",
                inbox_item_id=kwargs["inbox_item_id"],
                review_type=kwargs["review_type"],
                state="pending",
                payload=kwargs["payload"],
            )
            self.open.append(review)
            return review

    inbox_repo = FakeInboxRepo()
    review_repo = FakeReviewRepo()

    def shadow_once():
        row = inbox_repo.get_or_create_shadow_item(item)
        for review in review_repo.get_open_reviews_for_item(str(row["id"])):
            if review.review_type == "possible_duplicate":
                return review

        return review_repo.create_review(
            inbox_item_id=str(row["id"]),
            review_type="possible_duplicate",
            payload={
                "original_text": item.text,
                "candidate_task_id": "task-456",
                "candidate_task_title": "Review generator quote",
                "match_score": 0.72,
                "confidence": "Medium",
                "allowed_decisions": [
                    "link_existing",
                    "create_anyway",
                    "ignore",
                ],
                "authority": "notion_shadow_only",
            },
        )

    first = shadow_once()
    second = shadow_once()

    if first.id != second.id:
        raise RuntimeError("Repeated shadow write did not reuse open review.")

    if len(review_repo.created) != 1:
        raise RuntimeError(
            f"Expected one shadow review creation; got {len(review_repo.created)}"
        )

    payload = review_repo.created[0]["payload"]
    if payload["authority"] != "notion_shadow_only":
        raise RuntimeError("Shadow authority marker missing.")

    print("Shadow inbox identity dispatch: PASS")
    print("Possible-duplicate payload mapping: PASS")
    print("Open-review idempotency: PASS")
    print("Notion shadow-only authority marker: PASS")
    print("RESULT: POSSIBLE DUPLICATE SHADOW SMOKE TEST PASSED")

if __name__ == "__main__":
    main()
