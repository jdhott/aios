#!/usr/bin/env python3
from fastapi.testclient import TestClient

import aios.api.app as api_module


class FakeInboxRepository:
    def create_brain_dump_item(
        self,
        *,
        raw_text,
        notes,
        parser,
        source_metadata,
    ):
        parsed = parser(raw_text)
        return {
            "id": "inbox-test-1",
            "status": "pending",
            "source": "brain_dump",
            "text": raw_text,
            "clean_text": parsed.clean_text,
            "due_date": None,
            "project_hint": parsed.project_hint,
            "is_urgent": parsed.is_urgent,
            "is_important": parsed.is_important,
            "is_just_do_it": parsed.is_jdi,
        }


class FakeReview:
    def __init__(self, review_id):
        self.review_id = review_id

    def to_dict(self):
        return {
            "id": self.review_id,
            "review_type": "possible_duplicate",
            "state": "pending",
            "subject_text": "Check generator quote",
            "payload": {"score": 0.82},
            "options": [
                "link_existing",
                "create_anyway",
                "ignore",
            ],
            "inbox_item_id": "inbox-2",
            "created_at": None,
            "updated_at": None,
        }


class FakeReviewService:
    def list_pending_reviews(self):
        return [FakeReview("review-1")]

    def get_review(self, review_id):
        if review_id == "review-1":
            return FakeReview(review_id)
        return None


api_module._inbox_repository = lambda: FakeInboxRepository()
api_module._review_service = lambda: FakeReviewService()

client = TestClient(api_module.app)

health = client.get("/health")
assert health.status_code == 200
assert health.json()["status"] == "ok"

captured = client.post(
    "/inbox",
    json={
        "text": "need to test the app API",
        "notes": ["synthetic"],
    },
)
assert captured.status_code == 201
assert captured.json()["id"] == "inbox-test-1"
assert captured.json()["clean_text"] == "Test the app API"

reviews = client.get("/reviews")
assert reviews.status_code == 200
assert len(reviews.json()) == 1
assert reviews.json()[0]["id"] == "review-1"

review = client.get("/reviews/review-1")
assert review.status_code == 200
assert review.json()["review_type"] == "possible_duplicate"

missing = client.get("/reviews/missing")
assert missing.status_code == 404

print("Health endpoint: PASS")
print("Inbox capture endpoint: PASS")
print("Review list endpoint: PASS")
print("Review lookup endpoint: PASS")
print("404 review behavior: PASS")
print("RESULT: CLOUD RUN API V1 SMOKE TEST PASSED")
