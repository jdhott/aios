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
            review_id,
            "possible_duplicate",
            "resolved",
            "Garage flashlight",
            "shadow-row",
            {},
            ["link_existing", "create_anyway", "ignore"],
        )

class FakeInboxRepository:
    def __init__(self):
        self.rows = {
            "shadow-row": {
                "id": "shadow-row",
                "status": "pending",
                "source_item_id": "native-row",
                "source_metadata": {"shadow": True},
            },
            "native-row": {
                "id": "native-row",
                "status": "pending",
                "source_item_id": None,
                "source_metadata": {"capture_interface": "cloud_run_api_v1"},
            },
        }
        self.processed = []

    def get_row(self, inbox_id):
        return self.rows.get(inbox_id)

    def mark_processed(self, inbox_id):
        self.processed.append(inbox_id)
        if inbox_id in self.rows:
            self.rows[inbox_id]["status"] = "processed"

def exercise(action, created_task_ids=None):
    repo = FakeInboxRepository()
    api_module._review_service = lambda: FakeReviewService()
    api_module._inbox_repository = lambda: repo

    payload = {
        "action": action,
        "candidate_task_id": "task-existing",
        "candidate_task_title": "Kitchen flashlight",
    }
    if created_task_ids is not None:
        payload["created_task_ids"] = created_task_ids

    with TestClient(api_module.app) as client:
        response = client.post(
            "/reviews/review-1/possible-duplicate",
            json=payload,
        )

    assert response.status_code == 200, response.text
    assert repo.processed == ["shadow-row", "native-row"]
    assert repo.rows["shadow-row"]["status"] == "processed"
    assert repo.rows["native-row"]["status"] == "processed"

exercise("link_existing")
print("link_existing closes shadow + native rows: PASS")

exercise("ignore")
print("ignore closes shadow + native rows: PASS")

exercise("create_anyway", ["task-new"])
print("create_anyway closes shadow + native rows after task creation: PASS")

print("RESULT: CLOUD WORKFLOW LIFECYCLE FIX V1.1 SMOKE TEST PASSED")
