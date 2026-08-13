from __future__ import annotations
from typing import Protocol
from aios.ingestion.models import InboxItem

class InboxSource(Protocol):
    def list_pending_items(self) -> list[InboxItem]:
        ...

    def remove_item(self, item: InboxItem) -> None:
        """Remove or mark one source item processed after AIOS handles it."""
        ...
