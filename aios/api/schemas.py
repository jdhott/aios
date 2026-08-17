from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "aios-api"
    version: str
    environment: str
    auth_mode: str


class InboxCaptureRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
    notes: list[str] = Field(default_factory=list)


class InboxCaptureResponse(BaseModel):
    id: str
    status: str
    source: str
    text: str
    clean_text: str | None = None
    due_date: str | None = None
    project_hint: str | None = None
    is_urgent: bool = False
    is_important: bool = False
    is_just_do_it: bool = False


class ReviewResponse(BaseModel):
    id: str
    review_type: str
    state: str
    subject_text: str
    payload: dict[str, Any] = Field(default_factory=dict)
    options: list[str] = Field(default_factory=list)
    inbox_item_id: str
    created_at: str | None = None
    updated_at: str | None = None

API_REVIEW_RESOLUTION_SCHEMA_VERSION = "cloud-run-api-v1.2"

class PossibleDuplicateResolutionRequest(BaseModel):
    action: str
    candidate_task_id: str | None = None
    candidate_task_title: str | None = None
    title_choice: str | None = None
    created_task_ids: list[str] = Field(default_factory=list)

class ClarificationAwaitingAnswerRequest(BaseModel):
    question: str = Field(min_length=1, max_length=5000)

class ClarificationPendingConfirmationRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=10000)
    proposed_text: str = Field(min_length=1, max_length=10000)

class ClarificationResolutionRequest(BaseModel):
    selected_text: str = Field(min_length=1, max_length=10000)
    accepted_text: str = Field(min_length=1, max_length=10000)
