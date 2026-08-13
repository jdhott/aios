"""Source-neutral review interaction contracts for AIOS."""
from __future__ import annotations

from typing import Protocol, Any

from aios.ingestion.models import InboxItem


class InboxReviewUI(Protocol):
    """Interactive review surface for inbox decisions."""

    def show_possible_duplicate(
        self,
        item: InboxItem,
        matched_task: Any,
        score: float,
    ) -> bool:
        ...

    def get_possible_duplicate_action(
        self,
        item: InboxItem,
    ) -> str | None:
        ...
