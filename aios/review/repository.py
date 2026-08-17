from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from aios.review.models import (
    InboxReview,
    REVIEW_STATES,
    REVIEW_TYPES,
)
from aios.storage.supabase_store import SupabaseStore


def parse_datetime(
    value: Optional[str],
) -> Optional[datetime]:
    if not value:
        return None

    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


REVIEW_REPOSITORY_OPEN_QUEUE_VERSION = "app-service-boundary-v1-phase2.1"


class InboxReviewRepository:
    """Supabase persistence layer for inbox human-review workflows."""

    def __init__(
        self,
        store: SupabaseStore,
    ):
        self.store = store

    def row_to_review(
        self,
        row: dict[str, Any],
    ) -> InboxReview:
        return InboxReview(
            id=str(row["id"]),
            inbox_item_id=str(
                row["inbox_item_id"]
            ),
            review_type=row["review_type"],
            state=row["state"],
            payload=row.get("payload") or {},
            decision=row.get("decision"),
            created_at=parse_datetime(
                row.get("created_at")
            ),
            updated_at=parse_datetime(
                row.get("updated_at")
            ),
            resolved_at=parse_datetime(
                row.get("resolved_at")
            ),
        )

    def create_review(
        self,
        *,
        inbox_item_id: str,
        review_type: str,
        payload: Optional[dict[str, Any]] = None,
        state: str = "pending",
    ) -> InboxReview:
        if review_type not in REVIEW_TYPES:
            raise ValueError(
                f"Unsupported review_type: {review_type}"
            )

        if state not in REVIEW_STATES:
            raise ValueError(
                f"Unsupported review state: {state}"
            )

        response = (
            self.store.client
            .table("inbox_reviews")
            .insert(
                {
                    "inbox_item_id":
                        inbox_item_id,
                    "review_type":
                        review_type,
                    "state":
                        state,
                    "payload":
                        payload or {},
                }
            )
            .execute()
        )

        rows = response.data or []

        if not rows:
            raise RuntimeError(
                "Failed to create inbox review."
            )

        return self.row_to_review(
            rows[0]
        )

    def get_review(
        self,
        review_id: str,
    ) -> Optional[InboxReview]:
        response = (
            self.store.client
            .table("inbox_reviews")
            .select("*")
            .eq("id", review_id)
            .limit(1)
            .execute()
        )

        rows = response.data or []

        if not rows:
            return None

        return self.row_to_review(
            rows[0]
        )

    def get_open_reviews(
        self,
    ) -> list[InboxReview]:
        response = (
            self.store.client
            .table("inbox_reviews")
            .select("*")
            .neq("state", "resolved")
            .order("created_at")
            .execute()
        )

        return [
            self.row_to_review(row)
            for row in (response.data or [])
        ]


    def get_reviews_for_item(
        self,
        inbox_item_id: str,
    ) -> list[InboxReview]:
        """Return all reviews for one inbox item, including resolved."""
        response = (
            self.store.client
            .table("inbox_reviews")
            .select("*")
            .eq(
                "inbox_item_id",
                inbox_item_id,
            )
            .order("created_at")
            .execute()
        )

        return [
            self.row_to_review(row)
            for row in (
                response.data or []
            )
        ]


    def get_open_reviews_for_item(
        self,
        inbox_item_id: str,
    ) -> list[InboxReview]:
        response = (
            self.store.client
            .table("inbox_reviews")
            .select("*")
            .eq(
                "inbox_item_id",
                inbox_item_id,
            )
            .neq(
                "state",
                "resolved",
            )
            .order("created_at")
            .execute()
        )

        return [
            self.row_to_review(row)
            for row in (
                response.data or []
            )
        ]

    def get_recent_resolved_reviews(
        self,
        *,
        limit: int = 10,
    ) -> list[InboxReview]:
        response = (
            self.store.client
            .table("inbox_reviews")
            .select("*")
            .eq("state", "resolved")
            .order(
                "resolved_at",
                desc=True,
            )
            .limit(limit)
            .execute()
        )

        return [
            self.row_to_review(row)
            for row in (
                response.data or []
            )
        ]


    def update_state(
        self,
        review_id: str,
        state: str,
        *,
        payload: Optional[dict[str, Any]] = None,
    ) -> InboxReview:
        if state not in REVIEW_STATES:
            raise ValueError(
                f"Unsupported review state: {state}"
            )

        update_payload: dict[str, Any] = {
            "state": state,
        }

        if payload is not None:
            update_payload["payload"] = payload

        response = (
            self.store.client
            .table("inbox_reviews")
            .update(update_payload)
            .eq("id", review_id)
            .execute()
        )

        rows = response.data or []

        if not rows:
            raise RuntimeError(
                f"Failed to update inbox review: {review_id}"
            )

        return self.row_to_review(
            rows[0]
        )

    def resolve_review(
        self,
        review_id: str,
        *,
        decision: dict[str, Any],
    ) -> InboxReview:
        response = (
            self.store.client
            .table("inbox_reviews")
            .update(
                {
                    "state":
                        "resolved",
                    "decision":
                        decision,
                    "resolved_at": (
                        datetime.now(
                            timezone.utc
                        )
                        .isoformat()
                    ),
                }
            )
            .eq("id", review_id)
            .execute()
        )

        rows = response.data or []

        if not rows:
            raise RuntimeError(
                f"Failed to resolve inbox review: {review_id}"
            )

        return self.row_to_review(
            rows[0]
        )

    def delete_review(
        self,
        review_id: str,
    ) -> None:
        (
            self.store.client
            .table("inbox_reviews")
            .delete()
            .eq("id", review_id)
            .execute()
        )
