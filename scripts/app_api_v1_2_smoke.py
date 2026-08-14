#!/usr/bin/env python3
from dataclasses import dataclass
from fastapi.testclient import TestClient
import aios.api.app as api_module

@dataclass
class FakeReview:
    id: str
    review_type: str
    state: str
    subject_text: str
    inbox_item_id: str
    payload: dict
    options: list

    def to_dict(self):
        return {
            "id": self.id,
            "review_type": self.review_type,
            "state": self.state,
            "subject_text": self.subject_text,
            "payload": self.payload,
            "options": self.options,
            "inbox_item_id": self.inbox_item_id,
            "created_at": None,
            "updated_at": None,
        }

class FakeReviewService:
    def resolve_possible_duplicate(
        self, review_id, *, action,
        candidate_task_id=None,
        candidate_task_title=None,
        created_task_ids=None,
    ):
        if action == "create_anyway" and not created_task_ids:
            raise ValueError("create_anyway requires created_task_ids")
        return FakeReview(
            review_id, "possible_duplicate", "resolved",
            "Garage flashlight", "inbox-garage",
            {"candidate_task_id": candidate_task_id},
            ["link_existing", "create_anyway", "ignore"],
        )

    def mark_clarification_awaiting_answer(self, review_id, *, question):
        return FakeReview(
            review_id, "clarification", "awaiting_answer",
            "Plan canning", "inbox-canning",
            {"question": question}, [],
        )

    def mark_clarification_pending_confirmation(
        self, review_id, *, answer, proposed_text
    ):
        return FakeReview(
            review_id, "clarification", "pending_confirmation",
            "Plan canning", "inbox-canning",
            {"answer": answer, "proposed_text": proposed_text},
            [proposed_text],
        )

    def resolve_clarification(
        self, review_id, *, selected_text, accepted_text
    ):
        return FakeReview(
            review_id, "clarification", "resolved",
            "Plan canning", "inbox-canning",
            {"selected_text": selected_text, "accepted_text": accepted_text},
            [],
        )

class FakeInboxRepository:
    def __init__(self):
        self.processed = []
        self.rows = {
            "inbox-garage": {
                "id": "inbox-garage",
                "source_item_id": "native-garage",
                "source_metadata": {
                    "shadow": True,
                },
            },
            "native-garage": {
                "id": "native-garage",
                "source_item_id": None,
                "source_metadata": {
                    "capture_interface": "cloud_run_api_v1",
                },
            },
        }

    def get_row(self, inbox_id):
        return self.rows.get(inbox_id)

    def mark_processed(self, inbox_id):
        self.processed.append(inbox_id)

fake_service = FakeReviewService()
fake_inbox = FakeInboxRepository()
api_module._review_service = lambda: fake_service
api_module._inbox_repository = lambda: fake_inbox

with TestClient(api_module.app) as client:
    r = client.post(
        "/reviews/review-dup/possible-duplicate",
        json={
            "action": "link_existing",
            "candidate_task_id": "task-existing",
            "candidate_task_title": "Kitchen flashlight",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["state"] == "resolved"
    assert fake_inbox.processed == ["inbox-garage", "native-garage"]

    r = client.post(
        "/reviews/review-new/possible-duplicate",
        json={"action": "create_anyway"},
    )
    assert r.status_code == 409

    r = client.post(
        "/reviews/review-c/clarification/awaiting-answer",
        json={"question": "Which foods?"},
    )
    assert r.status_code == 200
    assert r.json()["state"] == "awaiting_answer"

    r = client.post(
        "/reviews/review-c/clarification/pending-confirmation",
        json={"answer": "Tomatoes", "proposed_text": "List tomatoes to can"},
    )
    assert r.status_code == 200
    assert r.json()["state"] == "pending_confirmation"

    r = client.post(
        "/reviews/review-c/clarification/resolve",
        json={
            "selected_text": "List tomatoes to can",
            "accepted_text": "List tomatoes to can",
        },
    )
    assert r.status_code == 200
    assert r.json()["state"] == "resolved"

print("Possible duplicate link-existing endpoint: PASS")
print("Duplicate inbox lifecycle: PASS")
print("create-anyway sequencing guard mapping: PASS")
print("Clarification awaiting-answer endpoint: PASS")
print("Clarification pending-confirmation endpoint: PASS")
print("Clarification resolve endpoint: PASS")
print("RESULT: CLOUD RUN API V1.2 SMOKE TEST PASSED")
