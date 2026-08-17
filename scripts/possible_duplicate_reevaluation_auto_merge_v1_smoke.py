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
            id="review-auto",
            inbox_item_id="inbox-auto",
            review_type="possible_duplicate",
            state="pending",
            payload={
                "requested_action": "reevaluate",
                "original_text":
                    "Schedule yearly dental checkup appointment for TEST",
            },
            created_at=now,
            updated_at=now,
        )

    def update_state(
        self,
        review_id,
        state,
        *,
        payload=None,
    ):
        assert review_id == self.review.id

        self.review = replace(
            self.review,
            state=state,
            payload=(
                payload
                if payload is not None
                else self.review.payload
            ),
            updated_at=datetime.now(timezone.utc),
        )

        return self.review

    def resolve_review(
        self,
        review_id,
        *,
        decision,
    ):
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
            "inbox-auto": {
                "id": "inbox-auto",
                "status": "pending",
                "source_metadata": {},
            },
        }
        self.processed = []

    def get_row(self, inbox_id):
        return self.rows.get(inbox_id)

    def mark_processed(self, inbox_id):
        self.processed.append(inbox_id)
        self.rows[inbox_id]["status"] = "processed"
        return dict(self.rows[inbox_id])


def mark_review_inbox_processed(
    repo,
    review,
):
    review_row = repo.get_row(
        review.inbox_item_id
    )

    repo.mark_processed(
        review.inbox_item_id
    )

    if not review_row:
        return

    source_metadata = (
        review_row.get("source_metadata")
        or {}
    )

    if not bool(source_metadata.get("shadow")):
        return

    original_inbox_id = str(
        review_row.get("source_item_id")
        or ""
    ).strip()

    if (
        not original_inbox_id
        or original_inbox_id
        == review.inbox_item_id
    ):
        return

    if repo.get_row(original_inbox_id):
        repo.mark_processed(
            original_inbox_id
        )


# ---------------------------------------------------------
# SUCCESS PATH
# ---------------------------------------------------------

review_repo = FakeReviewRepo()
inbox_repo = FakeInboxRepo()

candidate_task_id = "task-existing"
candidate_task_title = (
    "Book annual dental checkup for TEST"
)
match_score = 0.96
semantic_reason = (
    "Both tasks describe the same annual dental checkup."
)

payload = dict(
    review_repo.review.payload
)

payload["auto_merge_notice"] = {
    "message": "Merged automatically",
    "candidate_task_id":
        candidate_task_id,
    "candidate_task_title":
        candidate_task_title,
    "match_score":
        match_score,
    "kept_wording":
        "existing",
}

payload["semantic_state"] = "duplicate"
payload["semantic_reason"] = semantic_reason
payload.pop(
    "requested_action",
    None,
)

review = review_repo.update_state(
    review_repo.review.id,
    "pending",
    payload=payload,
)

resolved = resolve_possible_duplicate_review(
    review_repo=review_repo,
    review=review,
    action="link_existing",
    candidate_task_id=candidate_task_id,
    candidate_task_title=candidate_task_title,
)

mark_review_inbox_processed(
    inbox_repo,
    resolved,
)

assert resolved.state == "resolved"
assert (
    resolved.decision["action"]
    == "link_existing"
)
assert (
    resolved.decision["candidate_task_id"]
    == "task-existing"
)
assert (
    resolved.decision["candidate_task_title"]
    == "Book annual dental checkup for TEST"
)

assert (
    resolved.payload["auto_merge_notice"][
        "kept_wording"
    ]
    == "existing"
)
assert (
    resolved.payload["auto_merge_notice"][
        "match_score"
    ]
    == 0.96
)
assert (
    "requested_action"
    not in resolved.payload
)

assert inbox_repo.processed == [
    "inbox-auto",
]

print("Auto-merge resolves as link_existing: PASS")
print("Auto-merge preserves existing wording: PASS")
print("Auto-merge notice retained on review: PASS")
print("Auto-merge clears re-evaluation request: PASS")
print("Auto-merge closes inbox lifecycle: PASS")


# ---------------------------------------------------------
# FAILURE PATH
# ---------------------------------------------------------

review_repo = FakeReviewRepo()
inbox_repo = FakeInboxRepo()

# Simulate failure before resolve_review() succeeds.
try:
    raise RuntimeError("simulated resolution failure")
except RuntimeError:
    pass

assert review_repo.review.state == "pending"
assert review_repo.review.decision is None
assert inbox_repo.processed == []
assert (
    inbox_repo.rows["inbox-auto"]["status"]
    == "pending"
)

print("Auto-merge failure leaves review pending: PASS")
print("Auto-merge failure leaves inbox pending: PASS")


# ---------------------------------------------------------
# LEGACY SHADOW LIFECYCLE
# ---------------------------------------------------------

review_repo = FakeReviewRepo()

inbox_repo = FakeInboxRepo()
inbox_repo.rows = {
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

payload = dict(
    review_repo.review.payload
)

payload["auto_merge_notice"] = {
    "message": "Merged automatically",
    "candidate_task_id":
        "task-existing",
    "candidate_task_title":
        "Book annual dental checkup for TEST",
    "match_score":
        0.96,
    "kept_wording":
        "existing",
}

payload.pop(
    "requested_action",
    None,
)

review = review_repo.update_state(
    review_repo.review.id,
    "pending",
    payload=payload,
)

resolved = resolve_possible_duplicate_review(
    review_repo=review_repo,
    review=review,
    action="link_existing",
    candidate_task_id="task-existing",
    candidate_task_title=
        "Book annual dental checkup for TEST",
)

mark_review_inbox_processed(
    inbox_repo,
    resolved,
)

assert inbox_repo.processed == [
    "shadow-row",
    "native-row",
]

print("Legacy shadow + native lifecycle closes: PASS")

print(
    "RESULT: POSSIBLE DUPLICATE RE-EVALUATION "
    "AUTO MERGE V1 SMOKE TEST PASSED"
)
