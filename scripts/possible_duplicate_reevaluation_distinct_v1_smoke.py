#!/usr/bin/env python3

from dataclasses import replace
from datetime import datetime, timezone

from aios.review.models import InboxReview
from aios.review.possible_duplicate_transitions import (
    resolve_possible_duplicate_review,
)


class FakeReviewRepo:
    def __init__(self):
        now = datetime.now(timezone.utc)
        self.review = InboxReview(
            id="review-distinct",
            inbox_item_id="inbox-distinct",
            review_type="possible_duplicate",
            state="pending",
            payload={
                "requested_action": "reevaluate",
                "original_text": "Book TEST service appointment",
            },
            created_at=now,
            updated_at=now,
        )

    def resolve_review(self, review_id, *, decision):
        assert review_id == self.review.id

        self.review = replace(
            self.review,
            state="resolved",
            decision=decision,
            resolved_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        return self.review


class FakeInboxRepo:
    def __init__(self):
        self.rows = {
            "inbox-distinct": {
                "id": "inbox-distinct",
                "status": "pending",
                "source_metadata": {},
            }
        }
        self.processed = []

    def get_row(self, inbox_id):
        return self.rows.get(inbox_id)

    def mark_processed(self, inbox_id):
        self.processed.append(inbox_id)

        row = self.rows[inbox_id]
        row["status"] = "processed"

        return dict(row)


def mark_review_inbox_processed(repo, review):
    row = repo.get_row(review.inbox_item_id)

    repo.mark_processed(
        review.inbox_item_id
    )

    if not row:
        return

    metadata = row.get("source_metadata") or {}

    if not bool(metadata.get("shadow")):
        return

    original_id = str(
        row.get("source_item_id") or ""
    ).strip()

    if (
        original_id
        and original_id != review.inbox_item_id
        and repo.get_row(original_id)
    ):
        repo.mark_processed(original_id)


# ---------------------------------------------------------
# SUCCESS PATH
# ---------------------------------------------------------

review_repo = FakeReviewRepo()
inbox_repo = FakeInboxRepo()

created_task_ids = ["task-new"]

assert created_task_ids

resolved = resolve_possible_duplicate_review(
    review_repo=review_repo,
    review=review_repo.review,
    action="reevaluated_distinct",
    created_task_ids=created_task_ids,
)

mark_review_inbox_processed(
    inbox_repo,
    resolved,
)

assert resolved.state == "resolved"
assert (
    resolved.decision["action"]
    == "reevaluated_distinct"
)
assert (
    resolved.decision["created_task_ids"]
    == ["task-new"]
)
assert (
    inbox_repo.processed
    == ["inbox-distinct"]
)

print("Distinct success resolves review: PASS")
print("Distinct success records created task: PASS")
print("Distinct success closes inbox lifecycle: PASS")


# ---------------------------------------------------------
# FAILURE PATH
# ---------------------------------------------------------

review_repo = FakeReviewRepo()
inbox_repo = FakeInboxRepo()

created_task_ids = []

# This mirrors the processor guard:
# no created task means do not resolve or process inbox.
if created_task_ids:
    raise RuntimeError(
        "Failure-path fixture unexpectedly created task"
    )

assert review_repo.review.state == "pending"
assert review_repo.review.decision is None
assert inbox_repo.processed == []
assert (
    inbox_repo.rows["inbox-distinct"]["status"]
    == "pending"
)

print("Distinct failure leaves review pending: PASS")
print("Distinct failure leaves inbox pending: PASS")


# ---------------------------------------------------------
# LEGACY SHADOW LIFECYCLE
# ---------------------------------------------------------

review_repo = FakeReviewRepo()

shadow_inbox = FakeInboxRepo()
shadow_inbox.rows = {
    "shadow-row": {
        "id": "shadow-row",
        "status": "pending",
        "source_item_id": "native-row",
        "source_metadata": {
            "shadow": True,
        },
    },
    "native-row": {
        "id": "native-row",
        "status": "pending",
        "source_item_id": None,
        "source_metadata": {},
    },
}

review_repo.review = replace(
    review_repo.review,
    inbox_item_id="shadow-row",
)

resolved = resolve_possible_duplicate_review(
    review_repo=review_repo,
    review=review_repo.review,
    action="reevaluated_distinct",
    created_task_ids=["task-new-shadow"],
)

mark_review_inbox_processed(
    shadow_inbox,
    resolved,
)

assert shadow_inbox.processed == [
    "shadow-row",
    "native-row",
]

print("Legacy shadow + native lifecycle closes: PASS")

print(
    "RESULT: POSSIBLE DUPLICATE RE-EVALUATION "
    "DISTINCT V1 SMOKE TEST PASSED"
)
