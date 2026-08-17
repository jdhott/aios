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
    def __init__(self):
        self.resolutions = []

    def get_review(self, review_id):
        return FakeReview(
            review_id,
            "possible_duplicate",
            "pending",
            "Book the Honda Civic in for service",
            "inbox-honda",
            {},
            ["link_existing", "create_anyway", "ignore"],
        )

    def resolve_possible_duplicate(
        self,
        review_id,
        *,
        action,
        candidate_task_id=None,
        candidate_task_title=None,
        created_task_ids=None,
    ):
        self.resolutions.append(
            {
                "review_id": review_id,
                "action": action,
                "candidate_task_id": candidate_task_id,
                "candidate_task_title": candidate_task_title,
                "created_task_ids": created_task_ids,
            }
        )

        return FakeReview(
            review_id,
            "possible_duplicate",
            "resolved",
            "Book the Honda Civic in for service",
            "inbox-honda",
            {
                "candidate_task_id": candidate_task_id,
                "candidate_task_title": candidate_task_title,
            },
            ["link_existing", "create_anyway", "ignore"],
        )


class FakeInboxRepository:
    def __init__(self):
        self.processed = []

    def get_row(self, inbox_id):
        if inbox_id == "inbox-honda":
            return {
                "id": "inbox-honda",
                "source_item_id": None,
                "source_metadata": {},
            }
        return None

    def mark_processed(self, inbox_id):
        self.processed.append(inbox_id)


class FakeResult:
    def __init__(self, data):
        self.data = data


class FakeTaskTable:
    def __init__(self, tasks):
        self.tasks = tasks
        self.filters = {}
        self.update_values = None

    def select(self, *_args, **_kwargs):
        self.filters = {}
        self.update_values = None
        return self

    def update(self, values):
        self.filters = {}
        self.update_values = dict(values)
        return self

    def eq(self, field, value):
        self.filters[field] = value
        return self

    def limit(self, _limit):
        return self

    def execute(self):
        rows = [
            task
            for task in self.tasks.values()
            if all(
                task.get(field) == value
                for field, value in self.filters.items()
            )
        ]

        if self.update_values is not None:
            for row in rows:
                row.update(self.update_values)

        return FakeResult(
            [dict(row) for row in rows]
        )


class FakeClient:
    def __init__(self):
        self.tasks = {
            "task-honda": {
                "id": "task-honda",
                "title": "Schedule appointment for car service",
                "is_done": False,
                "is_archived": False,
            },
            "task-closed": {
                "id": "task-closed",
                "title": "Closed car service task",
                "is_done": True,
                "is_archived": False,
            },
        }

    def table(self, name):
        assert name == "tasks"
        return FakeTaskTable(self.tasks)


class FakeStore:
    def __init__(self):
        self.client = FakeClient()


fake_store = FakeStore()
fake_service = FakeReviewService()
fake_inbox = FakeInboxRepository()

api_module._store = lambda: fake_store
api_module._review_service = lambda: fake_service
api_module._inbox_repository = lambda: fake_inbox


with TestClient(api_module.app) as client:

    # ---------------------------------------------------------
    # 1. Use existing wording
    # ---------------------------------------------------------
    r = client.post(
        "/reviews/review-existing/possible-duplicate",
        json={
            "action": "link_existing",
            "candidate_task_id": "task-honda",
            "candidate_task_title":
                "Schedule appointment for car service",
            "title_choice": "existing",
        },
    )

    assert r.status_code == 200, r.text

    task = fake_store.client.tasks["task-honda"]

    assert task["id"] == "task-honda"
    assert task["title"] == "Schedule appointment for car service"

    resolution = fake_service.resolutions[-1]

    assert resolution["action"] == "link_existing"
    assert resolution["candidate_task_id"] == "task-honda"
    assert (
        resolution["candidate_task_title"]
        == "Schedule appointment for car service"
    )

    print("Use existing wording preserves title: PASS")
    print("Use existing wording preserves task ID: PASS")

    # ---------------------------------------------------------
    # 2. Use new wording
    # ---------------------------------------------------------
    fake_store.client.tasks["task-honda"]["title"] = (
        "Schedule appointment for car service"
    )

    r = client.post(
        "/reviews/review-new-wording/possible-duplicate",
        json={
            "action": "link_existing",
            "candidate_task_id": "task-honda",
            "candidate_task_title":
                "Schedule appointment for car service",
            "title_choice": "new",
        },
    )

    assert r.status_code == 200, r.text

    task = fake_store.client.tasks["task-honda"]

    assert task["id"] == "task-honda"
    assert task["title"] == "Book the Honda Civic in for service"

    resolution = fake_service.resolutions[-1]

    assert resolution["action"] == "link_existing"
    assert resolution["candidate_task_id"] == "task-honda"
    assert (
        resolution["candidate_task_title"]
        == "Book the Honda Civic in for service"
    )

    print("Use new wording renames existing task: PASS")
    print("Use new wording preserves task ID: PASS")

    # ---------------------------------------------------------
    # 3. Invalid title choice
    # ---------------------------------------------------------
    r = client.post(
        "/reviews/review-invalid/possible-duplicate",
        json={
            "action": "link_existing",
            "candidate_task_id": "task-honda",
            "title_choice": "better",
        },
    )

    assert r.status_code == 422, r.text
    print("Invalid title choice rejected: PASS")

    # ---------------------------------------------------------
    # 4. title_choice cannot accompany create_anyway
    # ---------------------------------------------------------
    r = client.post(
        "/reviews/review-invalid-action/possible-duplicate",
        json={
            "action": "create_anyway",
            "title_choice": "new",
        },
    )

    assert r.status_code == 422, r.text
    print("Title choice restricted to link_existing: PASS")

    # ---------------------------------------------------------
    # 5. Candidate ID required
    # ---------------------------------------------------------
    r = client.post(
        "/reviews/review-no-candidate/possible-duplicate",
        json={
            "action": "link_existing",
            "title_choice": "existing",
        },
    )

    assert r.status_code == 422, r.text
    print("Missing candidate task ID rejected: PASS")

    # ---------------------------------------------------------
    # 6. Closed task cannot be renamed/merged
    # ---------------------------------------------------------
    r = client.post(
        "/reviews/review-closed/possible-duplicate",
        json={
            "action": "link_existing",
            "candidate_task_id": "task-closed",
            "title_choice": "new",
        },
    )

    assert r.status_code == 409, r.text
    assert (
        fake_store.client.tasks["task-closed"]["title"]
        == "Closed car service task"
    )

    print("Closed candidate merge rejected: PASS")


print(
    "RESULT: POSSIBLE DUPLICATE TITLE CHOICE V1 "
    "SMOKE TEST PASSED"
)
