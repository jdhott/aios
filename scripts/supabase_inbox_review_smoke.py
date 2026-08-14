#!/usr/bin/env python3
"""Controlled live smoke for Supabase inbox review persistence."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from dotenv import find_dotenv, load_dotenv

from aios.review.repository import InboxReviewRepository
from aios.storage.inbox_repository import InboxRepository
from aios.storage.supabase_store import SupabaseStore


def main() -> None:
    load_dotenv(
        find_dotenv() or ".env",
        override=True,
    )

    store = SupabaseStore()
    inbox_repo = InboxRepository(store)
    review_repo = InboxReviewRepository(store)

    marker = "AIOS_REVIEW_SMOKE_" + uuid4().hex
    inbox_id = None
    review_ids: list[str] = []

    try:
        inbox_row = inbox_repo.create_item(
            text=f"Review smoke {marker}",
            source="brain_dump",
            source_metadata={
                "test": True,
                "created_by":
                    "scripts.supabase_inbox_review_smoke",
                "created_at":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),
            },
        )
        inbox_id = str(
            inbox_row["id"]
        )

        # -------------------------------------------------------------
        # Possible duplicate: simple terminal decision.
        # -------------------------------------------------------------
        duplicate = review_repo.create_review(
            inbox_item_id=inbox_id,
            review_type="possible_duplicate",
            payload={
                "candidate_task_id":
                    "test-task-123",
                "candidate_task_title":
                    "Existing generator quote task",
                "match_score":
                    0.72,
                "confidence":
                    "Medium",
                "allowed_decisions": [
                    "link_existing",
                    "create_anyway",
                    "ignore",
                ],
            },
        )
        review_ids.append(
            duplicate.id
        )

        if duplicate.state != "pending":
            raise RuntimeError(
                "Possible-duplicate review did not start pending."
            )

        duplicate_resolved = (
            review_repo.resolve_review(
                duplicate.id,
                decision={
                    "action":
                        "create_anyway",
                },
            )
        )

        if (
            duplicate_resolved.state
            != "resolved"
        ):
            raise RuntimeError(
                "Possible-duplicate review did not resolve."
            )

        if (
            duplicate_resolved.decision
            or {}
        ).get("action") != "create_anyway":
            raise RuntimeError(
                "Possible-duplicate decision was not persisted."
            )

        # -------------------------------------------------------------
        # Clarification: exercise intermediate workflow states.
        # -------------------------------------------------------------
        clarification = review_repo.create_review(
            inbox_item_id=inbox_id,
            review_type="clarification",
            payload={
                "original_text":
                    "Plan canning",
                "proposal":
                    "List the foods to preserve by canning this year",
            },
        )
        review_ids.append(
            clarification.id
        )

        awaiting = review_repo.update_state(
            clarification.id,
            "awaiting_answer",
            payload={
                "original_text":
                    "Plan canning",
                "question":
                    "Which foods do you want to preserve?",
            },
        )

        if awaiting.state != "awaiting_answer":
            raise RuntimeError(
                "Clarification did not enter awaiting_answer."
            )

        pending_confirmation = (
            review_repo.update_state(
                clarification.id,
                "pending_confirmation",
                payload={
                    "original_text":
                        "Plan canning",
                    "user_answer":
                        "Tomatoes, peaches, and relish",
                    "proposal":
                        "List tomatoes, peaches, and relish to preserve by canning this year",
                },
            )
        )

        if (
            pending_confirmation.state
            != "pending_confirmation"
        ):
            raise RuntimeError(
                "Clarification did not enter pending_confirmation."
            )

        clarification_resolved = (
            review_repo.resolve_review(
                clarification.id,
                decision={
                    "action":
                        "accept_wording",
                    "accepted_text":
                        "List tomatoes, peaches, and relish to preserve by canning this year",
                },
            )
        )

        if (
            clarification_resolved.state
            != "resolved"
        ):
            raise RuntimeError(
                "Clarification review did not resolve."
            )

        if not (
            clarification_resolved
            .decision
            or {}
        ).get("accepted_text"):
            raise RuntimeError(
                "Accepted clarification wording was not persisted."
            )

        open_reviews = (
            review_repo
            .get_open_reviews_for_item(
                inbox_id
            )
        )

        if open_reviews:
            raise RuntimeError(
                "Resolved reviews still appear as open."
            )

        print("Temporary inbox item creation: PASS")
        print("Possible-duplicate review creation: PASS")
        print("Possible-duplicate terminal decision: PASS")
        print("Clarification awaiting-answer state: PASS")
        print("Clarification pending-confirmation state: PASS")
        print("Clarification accepted wording persistence: PASS")
        print("Resolved review filtering: PASS")
        print(
            "RESULT: SUPABASE INBOX REVIEW POC "
            "SMOKE TEST PASSED"
        )

    finally:
        for review_id in review_ids:
            review_repo.delete_review(
                review_id
            )

        if inbox_id:
            inbox_repo.delete_item(
                inbox_id
            )

        print(
            "Temporary review/inbox cleanup: PASS"
        )


if __name__ == "__main__":
    main()
