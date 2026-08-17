from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from aios.review.models import InboxReview
from aios.ingestion.capture_metadata import parse_capture_metadata
from aios.review.clarification_transitions import (
    mark_clarification_awaiting_answer,
    mark_clarification_pending_confirmation,
    resolve_clarification_review,
)
from aios.review.possible_duplicate_transitions import (
    resolve_possible_duplicate_review,
)
from aios.review.repository import InboxReviewRepository
from aios.storage.inbox_repository import InboxRepository
from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_repository import TaskRepository

APP_REVIEW_READ_SERVICE_VERSION = "app-service-boundary-v1-phase2.1"
APP_REVIEW_RESOLUTION_SERVICE_VERSION = "app-service-boundary-v1-phase2.2"

POSSIBLE_DUPLICATE_OPTIONS = [
    "link_existing",
    "create_anyway",
    "ignore",
]


@dataclass(frozen=True)
class AppReview:
    id: str
    review_type: str
    state: str
    subject_text: str
    payload: dict[str, Any] = field(default_factory=dict)
    options: list[str] = field(default_factory=list)
    inbox_item_id: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key in ("created_at", "updated_at"):
            value = data.get(key)
            if value is not None:
                data[key] = value.isoformat()
        return data


class ReviewService:
    """Read-only app-facing service for authoritative Supabase reviews."""

    def __init__(
        self,
        *,
        store: SupabaseStore | None = None,
        review_repository: InboxReviewRepository | None = None,
        inbox_repository: InboxRepository | None = None,
        task_repository: TaskRepository | None = None,
    ):
        if store is None and (
            review_repository is None
            or inbox_repository is None
            or task_repository is None
        ):
            store = SupabaseStore()

        self.review_repository = (
            review_repository
            or InboxReviewRepository(store)
        )
        self.inbox_repository = (
            inbox_repository
            or InboxRepository(store)
        )
        self.task_repository = (
            task_repository
            or TaskRepository(store)
        )


    def request_clarification_question(
        self,
        review_id: str,
    ) -> AppReview:
        review = self._require_review(
            review_id,
            review_type="clarification",
        )

        payload = dict(review.payload or {})
        payload["requested_action"] = "ask_question"

        updated = self.review_repository.update_state(
            review.id,
            "pending",
            payload=payload,
        )

        return self._to_app_review(updated)


    def submit_clarification_answer(
        self,
        review_id: str,
        *,
        answer: str,
    ) -> AppReview:
        review = self._require_review(
            review_id,
            review_type="clarification",
        )

        clean_answer = str(answer or "").strip()

        if not clean_answer:
            raise ValueError(
                "Clarification answer cannot be blank."
            )

        payload = dict(review.payload or {})
        payload["answer"] = clean_answer
        payload["requested_action"] = "process_answer"

        updated = self.review_repository.update_state(
            review.id,
            "awaiting_answer",
            payload=payload,
        )

        return self._to_app_review(updated)


    def mark_clarification_awaiting_answer(
        self,
        review_id: str,
        *,
        question: str,
    ) -> AppReview:
        review = self._require_review(
            review_id,
            review_type="clarification",
        )
        updated = mark_clarification_awaiting_answer(
            review_repo=self.review_repository,
            review=review,
            question=question,
        )
        return self._to_app_review(updated)

    def mark_clarification_pending_confirmation(
        self,
        review_id: str,
        *,
        answer: str,
        proposed_text: str,
    ) -> AppReview:
        review = self._require_review(
            review_id,
            review_type="clarification",
        )
        updated = mark_clarification_pending_confirmation(
            review_repo=self.review_repository,
            review=review,
            answer=answer,
            proposed_text=proposed_text,
        )
        return self._to_app_review(updated)

    def resolve_clarification(
        self,
        review_id: str,
        *,
        selected_text: str,
        accepted_text: str,
    ) -> AppReview:
        review = self._require_review(
            review_id,
            review_type="clarification",
        )

        task_id = str(
            (review.payload or {}).get("task_id")
            or ""
        ).strip()

        if not task_id:
            raise ValueError(
                "Clarification review has no authoritative task_id."
            )

        capture = parse_capture_metadata(
            accepted_text
        )

        clean_title = str(
            capture.clean_text or ""
        ).strip()

        if not clean_title:
            raise ValueError(
                "Accepted clarification produced an empty task title."
            )

        values: dict[str, Any] = {
            "title": clean_title,
            "status": "Ready",
            "is_just_do_it": bool(
                capture.is_jdi
            ),
        }

        if capture.is_urgent:
            values["urgency"] = "High Urgency"

        if capture.is_important:
            values["importance"] = "High Importance"

        if capture.due_date:
            values["due_at"] = (
                capture.due_date.isoformat()
            )

        if capture.project_hint:
            values["suggested_project"] = (
                capture.project_hint
            )

        # Human acceptance is authoritative. Update the task first.
        # If this fails, the review remains open.
        self.task_repository.update_task(
            task_id,
            values=values,
        )

        resolved = resolve_clarification_review(
            review_repo=self.review_repository,
            review=review,
            selected_text=selected_text,
            accepted_text=clean_title,
        )

        return self._to_app_review(resolved)

    def request_possible_duplicate_reevaluation(
        self,
        review_id: str,
    ) -> AppReview:
        review = self._require_review(
            review_id,
            review_type="possible_duplicate",
        )

        payload = dict(review.payload or {})
        payload["requested_action"] = "reevaluate"

        updated = self.review_repository.update_state(
            review.id,
            "pending",
            payload=payload,
        )

        return self._to_app_review(updated)


    def request_possible_duplicate_create_anyway(
        self,
        review_id: str,
    ) -> AppReview:
        review = self._require_review(
            review_id,
            review_type="possible_duplicate",
        )

        payload = dict(review.payload or {})
        payload["requested_action"] = "create_anyway"

        updated = self.review_repository.update_state(
            review.id,
            "pending",
            payload=payload,
        )

        return self._to_app_review(updated)


    def resolve_possible_duplicate(
        self,
        review_id: str,
        *,
        action: str,
        candidate_task_id: str | None = None,
        candidate_task_title: str | None = None,
        created_task_ids: list[str] | None = None,
    ) -> AppReview:
        review = self._require_review(
            review_id,
            review_type="possible_duplicate",
        )
        if action == "create_anyway" and not created_task_ids:
            raise ValueError(
                "create_anyway requires created_task_ids so the "
                "review cannot resolve before task creation succeeds."
            )
        resolved = resolve_possible_duplicate_review(
            review_repo=self.review_repository,
            review=review,
            action=action,
            candidate_task_id=candidate_task_id,
            candidate_task_title=candidate_task_title,
            created_task_ids=created_task_ids,
        )
        return self._to_app_review(resolved)

    def _require_review(
        self,
        review_id: str,
        *,
        review_type: str,
    ) -> InboxReview:
        review = self.review_repository.get_review(review_id)
        if review is None:
            raise KeyError(f"Review not found: {review_id}")
        if review.review_type != review_type:
            raise ValueError(
                f"Expected {review_type} review, got {review.review_type!r}"
            )
        if review.state == "resolved":
            raise ValueError(f"Review is already resolved: {review_id}")
        return review

    def list_pending_reviews(
        self,
        *,
        review_types: Iterable[str] | None = None,
    ) -> list[AppReview]:
        allowed = (
            set(review_types)
            if review_types is not None
            else None
        )

        reviews = self.review_repository.get_open_reviews()

        if allowed is not None:
            reviews = [
                review
                for review in reviews
                if review.review_type in allowed
            ]

        return [self._to_app_review(review) for review in reviews]

    def list_recent_auto_merge_notices(
        self,
        *,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        reviews = (
            self.review_repository
            .get_recent_resolved_reviews(
                limit=limit,
            )
        )

        notices = []
        cutoff = (
            datetime.now(timezone.utc)
            - timedelta(minutes=10)
        )

        for review in reviews:
            if review.review_type != "possible_duplicate":
                continue

            if (
                review.resolved_at is None
                or review.resolved_at < cutoff
            ):
                continue

            payload = dict(review.payload or {})
            notice = payload.get("auto_merge_notice")

            if not isinstance(notice, dict):
                continue

            notices.append(
                {
                    "id": review.id,
                    "review_type":
                        review.review_type,
                    "resolved_at": (
                        review.resolved_at.isoformat()
                        if review.resolved_at
                        else None
                    ),
                    **notice,
                }
            )

        return notices


    def get_review(
        self,
        review_id: str,
    ) -> AppReview | None:
        review = self.review_repository.get_review(review_id)
        if review is None:
            return None
        return self._to_app_review(review)

    def _to_app_review(
        self,
        review: InboxReview,
    ) -> AppReview:
        inbox_row = self.inbox_repository.get_row(
            review.inbox_item_id
        ) or {}

        subject_text = str(
            inbox_row.get("clean_text")
            or inbox_row.get("text")
            or review.payload.get("original_text")
            or review.payload.get("subject_text")
            or ""
        ).strip()

        return AppReview(
            id=review.id,
            review_type=review.review_type,
            state=review.state,
            subject_text=subject_text,
            payload=dict(review.payload or {}),
            options=self._options_for(review),
            inbox_item_id=review.inbox_item_id,
            created_at=review.created_at,
            updated_at=review.updated_at,
        )

    @staticmethod
    def _options_for(
        review: InboxReview,
    ) -> list[str]:
        if review.review_type == "possible_duplicate":
            return list(POSSIBLE_DUPLICATE_OPTIONS)

        if review.review_type == "clarification":
            payload = review.payload or {}

            suggestions = payload.get("suggestions")
            if isinstance(suggestions, list):
                return [
                    str(value)
                    for value in suggestions
                    if value
                ]

            proposed_text = payload.get("proposed_text")
            if proposed_text:
                return [str(proposed_text)]

        return []
