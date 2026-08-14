from __future__ import annotations

from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

from aios.api.config import (
    get_api_settings,
    validate_runtime_environment,
)

from aios.api.schemas import (
    HealthResponse,
    InboxCaptureRequest,
    InboxCaptureResponse,
    ReviewResponse,
    PossibleDuplicateResolutionRequest,
    ClarificationAwaitingAnswerRequest,
    ClarificationPendingConfirmationRequest,
    ClarificationResolutionRequest,
)
from aios.ingestion.capture_metadata import parse_capture_metadata
from aios.services.review_service import ReviewService
from aios.storage.inbox_repository import InboxRepository
from aios.storage.supabase_store import SupabaseStore


AIOS_API_VERSION = "cloud-run-api-v1-scaffold"
AIOS_API_SECURITY_VERSION = "cloud-run-api-v1.1-security"
AIOS_API_REVIEW_RESOLUTION_VERSION = "cloud-run-api-v1.2"
AIOS_REVIEW_LIFECYCLE_FIX_VERSION = "cloud-workflow-lifecycle-v1.1"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    validate_runtime_environment()
    yield


app = FastAPI(
    title="AIOS API",
    version=AIOS_API_VERSION,
    description=(
        "App-facing HTTP boundary for AIOS. "
        "Supabase is authoritative; Notion is not required by these endpoints."
    ),
    lifespan=lifespan,
)


def _store() -> SupabaseStore:
    return SupabaseStore()


def _inbox_repository() -> InboxRepository:
    return InboxRepository(_store())


def _review_service() -> ReviewService:
    store = _store()
    return ReviewService(
        store=store,
        review_repository=None,
        inbox_repository=None,
    )


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["system"],
)
def health() -> HealthResponse:
    settings = get_api_settings()
    return HealthResponse(
        version=AIOS_API_VERSION,
        environment=settings.environment,
        auth_mode=settings.auth_mode,
    )


@app.post(
    "/inbox",
    response_model=InboxCaptureResponse,
    status_code=201,
    tags=["inbox"],
)
def capture_inbox(
    request: InboxCaptureRequest,
) -> InboxCaptureResponse:
    row = _inbox_repository().create_brain_dump_item(
        raw_text=request.text,
        notes=request.notes,
        parser=parse_capture_metadata,
        source_metadata={
            "capture_interface": "cloud_run_api_v1",
        },
    )

    return InboxCaptureResponse(
        id=str(row["id"]),
        status=str(row.get("status") or "pending"),
        source=str(row.get("source") or "brain_dump"),
        text=str(row.get("text") or request.text),
        clean_text=row.get("clean_text"),
        due_date=(
            str(row["due_date"])
            if row.get("due_date") is not None
            else None
        ),
        project_hint=row.get("project_hint"),
        is_urgent=bool(row.get("is_urgent", False)),
        is_important=bool(row.get("is_important", False)),
        is_just_do_it=bool(row.get("is_just_do_it", False)),
    )


@app.get(
    "/reviews",
    response_model=list[ReviewResponse],
    tags=["reviews"],
)
def list_reviews() -> list[ReviewResponse]:
    reviews = _review_service().list_pending_reviews()

    return [
        ReviewResponse(**review.to_dict())
        for review in reviews
    ]


@app.get(
    "/reviews/{review_id}",
    response_model=ReviewResponse,
    tags=["reviews"],
)
def get_review(
    review_id: str,
) -> ReviewResponse:
    review = _review_service().get_review(review_id)

    if review is None:
        raise HTTPException(
            status_code=404,
            detail="Review not found",
        )

    return ReviewResponse(**review.to_dict())


def _review_error(exc: Exception) -> HTTPException:
    if isinstance(exc, KeyError):
        return HTTPException(status_code=404, detail=str(exc).strip("'"))
    return HTTPException(status_code=409, detail=str(exc))

def _mark_review_inbox_processed(review: ReviewResponse) -> None:
    if not review.inbox_item_id:
        return

    repo = _inbox_repository()

    review_row = repo.get_row(review.inbox_item_id)

    repo.mark_processed(review.inbox_item_id)

    if not review_row:
        return

    source_metadata = review_row.get("source_metadata") or {}

    if not bool(source_metadata.get("shadow")):
        return

    original_inbox_id = str(
        review_row.get("source_item_id") or ""
    ).strip()

    if not original_inbox_id:
        return

    if original_inbox_id == review.inbox_item_id:
        return

    original_row = repo.get_row(original_inbox_id)

    if original_row is None:
        return

    repo.mark_processed(original_inbox_id)

@app.post(
    "/reviews/{review_id}/possible-duplicate",
    response_model=ReviewResponse,
    tags=["reviews"],
)
def resolve_possible_duplicate_http(
    review_id: str,
    request: PossibleDuplicateResolutionRequest,
) -> ReviewResponse:
    if request.action not in {"link_existing", "create_anyway", "ignore"}:
        raise HTTPException(
            status_code=422,
            detail="Unsupported possible duplicate action",
        )
    try:
        resolved = _review_service().resolve_possible_duplicate(
            review_id,
            action=request.action,
            candidate_task_id=request.candidate_task_id,
            candidate_task_title=request.candidate_task_title,
            created_task_ids=request.created_task_ids or None,
        )
    except (KeyError, ValueError) as exc:
        raise _review_error(exc) from exc

    response = ReviewResponse(**resolved.to_dict())
    _mark_review_inbox_processed(response)
    return response

@app.post(
    "/reviews/{review_id}/clarification/awaiting-answer",
    response_model=ReviewResponse,
    tags=["reviews"],
)
def clarification_awaiting_answer_http(
    review_id: str,
    request: ClarificationAwaitingAnswerRequest,
) -> ReviewResponse:
    try:
        updated = _review_service().mark_clarification_awaiting_answer(
            review_id,
            question=request.question,
        )
    except (KeyError, ValueError) as exc:
        raise _review_error(exc) from exc
    return ReviewResponse(**updated.to_dict())

@app.post(
    "/reviews/{review_id}/clarification/pending-confirmation",
    response_model=ReviewResponse,
    tags=["reviews"],
)
def clarification_pending_confirmation_http(
    review_id: str,
    request: ClarificationPendingConfirmationRequest,
) -> ReviewResponse:
    try:
        updated = _review_service().mark_clarification_pending_confirmation(
            review_id,
            answer=request.answer,
            proposed_text=request.proposed_text,
        )
    except (KeyError, ValueError) as exc:
        raise _review_error(exc) from exc
    return ReviewResponse(**updated.to_dict())

@app.post(
    "/reviews/{review_id}/clarification/resolve",
    response_model=ReviewResponse,
    tags=["reviews"],
)
def clarification_resolve_http(
    review_id: str,
    request: ClarificationResolutionRequest,
) -> ReviewResponse:
    try:
        resolved = _review_service().resolve_clarification(
            review_id,
            selected_text=request.selected_text,
            accepted_text=request.accepted_text,
        )
    except (KeyError, ValueError) as exc:
        raise _review_error(exc) from exc

    # Review-state only. Underlying task mutation remains separate.
    return ReviewResponse(**resolved.to_dict())
