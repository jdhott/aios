from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


REVIEW_TYPES = {
    "clarification",
    "possible_duplicate",
}

REVIEW_STATES = {
    "pending",
    "awaiting_answer",
    "pending_confirmation",
    "resolved",
}


@dataclass(frozen=True)
class InboxReview:
    id: str
    inbox_item_id: str
    review_type: str
    state: str
    payload: dict[str, Any] = field(default_factory=dict)
    decision: Optional[dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
