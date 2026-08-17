#!/usr/bin/env python3
from dataclasses import replace
from datetime import datetime, timezone

from aios.review.models import InboxReview
from aios.services.review_service import ReviewService


class FakeReviewRepository:
    def __init__(self):
        now = datetime.now(timezone.utc)
        self.reviews = {
            "clarify-1": InboxReview(
                id="clarify-1",
                inbox_item_id="inbox-1",
                review_type="clarification",
                state="pending",
                payload={
                    "original_text": "Plan canning",
                    "task_id": "task-clarify",
                },
                created_at=now,
                updated_at=now,
            ),
            "clarify-legacy": InboxReview(
                id="clarify-legacy",
                inbox_item_id="inbox-legacy",
                review_type="clarification",
                state="pending",
                payload={
                    "original_text": "Legacy clarification",
                    "notion_task_page_id": "notion-legacy-1",
                    "authority": "notion_shadow_only",
                },
                created_at=now,
                updated_at=now,
            ),
            "duplicate-1": InboxReview(
                id="duplicate-1",
                inbox_item_id="inbox-2",
                review_type="possible_duplicate",
                state="pending",
                payload={"candidate_task_title": "Review generator quote"},
                created_at=now,
                updated_at=now,
            ),
            "duplicate-create": InboxReview(
                id="duplicate-create",
                inbox_item_id="inbox-3",
                review_type="possible_duplicate",
                state="pending",
                payload={},
                created_at=now,
                updated_at=now,
            ),
        }

    def get_review(self, review_id):
        return self.reviews.get(review_id)

    def get_open_reviews(self):
        return [r for r in self.reviews.values() if r.state != "resolved"]

    def update_state(self, review_id, state, *, payload=None):
        current = self.reviews[review_id]
        updated = replace(
            current,
            state=state,
            payload=payload if payload is not None else current.payload,
            updated_at=datetime.now(timezone.utc),
        )
        self.reviews[review_id] = updated
        return updated

    def resolve_review(self, review_id, *, decision):
        current = self.reviews[review_id]
        updated = replace(
            current,
            state="resolved",
            decision=decision,
            updated_at=datetime.now(timezone.utc),
            resolved_at=datetime.now(timezone.utc),
        )
        self.reviews[review_id] = updated
        return updated


class FakeTaskRepository:
    def __init__(self):
        self.updated = []
        self.tasks = {
            "task-clarify": {
                "id": "task-clarify",
                "title": "Clarify next action: Plan canning",
            },
            "task-legacy": {
                "id": "task-legacy",
                "title": "Clarify next action: Legacy clarification",
                "legacy_notion_id": "notion-legacy-1",
            },
        }

    def get_task_by_legacy_notion_id(
        self,
        notion_id,
    ):
        for task in self.tasks.values():
            if task.get("legacy_notion_id") == notion_id:
                class TaskRow:
                    pass
                result = TaskRow()
                result.id = task["id"]
                return result
        return None

    def update_task(
        self,
        task_id,
        *,
        values,
    ):
        if task_id not in self.tasks:
            raise KeyError(
                f"Task not found: {task_id}"
            )

        self.tasks[task_id].update(values)

        self.updated.append(
            {
                "task_id": task_id,
                "values": dict(values),
            }
        )

        return self.tasks[task_id]


class FakeInboxRepository:
    rows = {
        "inbox-1": {"id": "inbox-1", "clean_text": "Plan canning"},
        "inbox-2": {"id": "inbox-2", "clean_text": "Check generator quote"},
        "inbox-3": {"id": "inbox-3", "clean_text": "Check generator quote again"},
        "inbox-legacy": {
            "id": "inbox-legacy",
            "clean_text": "Legacy clarification",
        },
    }

    def get_row(self, inbox_id):
        return self.rows.get(inbox_id)


task_repo = FakeTaskRepository()

service = ReviewService(
    review_repository=FakeReviewRepository(),
    inbox_repository=FakeInboxRepository(),
    task_repository=task_repo,
)

r = service.mark_clarification_awaiting_answer(
    "clarify-1",
    question="Which foods do you want to preserve?",
)
assert r.state == "awaiting_answer"
assert r.payload["question"] == "Which foods do you want to preserve?"

r = service.mark_clarification_pending_confirmation(
    "clarify-1",
    answer="Tomatoes and peaches",
    proposed_text="List tomatoes and peaches to preserve by canning",
)
assert r.state == "pending_confirmation"
assert r.payload["answer"] == "Tomatoes and peaches"

r = service.resolve_clarification(
    "clarify-1",
    selected_text="List tomatoes and peaches to preserve by canning",
    accepted_text="List tomatoes and peaches to preserve by canning",
)
assert r.state == "resolved"

assert task_repo.updated == [
    {
        "task_id": "task-clarify",
        "values": {
            "title":
                "List tomatoes and peaches to preserve by canning",
            "status": "Ready",
            "is_just_do_it": False,
        },
    }
]

r = service.resolve_possible_duplicate(
    "duplicate-1",
    action="ignore",
    candidate_task_id="task-existing",
    candidate_task_title="Review generator quote",
)
assert r.state == "resolved"

try:
    service.resolve_possible_duplicate(
        "duplicate-create",
        action="create_anyway",
    )
except ValueError as exc:
    assert "created_task_ids" in str(exc)
else:
    raise RuntimeError("create_anyway resolved before task creation")

r = service.resolve_possible_duplicate(
    "duplicate-create",
    action="create_anyway",
    created_task_ids=["task-new"],
)
assert r.state == "resolved"

legacy = service.get_review(
    "clarify-legacy"
)
assert legacy is not None
assert legacy.payload["task_id"] == "task-legacy"

r = service.delete_review_task(
    "clarify-legacy"
)
assert r.state == "resolved"

legacy_updates = [
    item
    for item in task_repo.updated
    if item["task_id"] == "task-legacy"
]

assert legacy_updates == [
    {
        "task_id": "task-legacy",
        "values": {
            "is_archived": True,
            "is_open": False,
        },
    }
]

try:
    service.resolve_clarification(
        "clarify-1",
        selected_text="again",
        accepted_text="again",
    )
except ValueError as exc:
    assert "already resolved" in str(exc)
else:
    raise RuntimeError("Resolved review accepted another transition")

print("Clarification pending → awaiting_answer: PASS")
print("Clarification awaiting_answer → pending_confirmation: PASS")
print("Clarification pending_confirmation → resolved: PASS")
print("Possible duplicate ignore resolution: PASS")
print("create_anyway sequencing guard: PASS")
print("create_anyway post-create resolution: PASS")
print("legacy clarification task-ID fallback: PASS")
print("clarification delete-task lifecycle: PASS")
print("resolved-review double transition rejection: PASS")
print("RESULT: APP REVIEW RESOLUTION SERVICE PHASE 2.2 SMOKE TEST PASSED")
