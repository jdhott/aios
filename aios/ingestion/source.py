from __future__ import annotations
from typing import Protocol
from aios.ingestion.models import InboxItem

class InboxSource(Protocol):
    def list_pending_items(self) -> list[InboxItem]:
        ...
