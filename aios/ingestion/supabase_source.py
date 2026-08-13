from __future__ import annotations

from typing import Optional

from aios.ingestion.models import InboxItem
from aios.storage.inbox_repository import InboxRepository
from aios.storage.supabase_store import SupabaseStore


class SupabaseInboxSource:
    """
    Inactive POC inbox source for the future AIOS app.

    Production Brain Dump ingestion remains on Notion until an explicit cutover.
    """

    def __init__(
        self,
        repository: Optional[InboxRepository] = None,
    ):
        self.repository = (
            repository
            or InboxRepository(SupabaseStore())
        )

    def list_pending_items(
        self,
    ) -> list[InboxItem]:
        return self.repository.get_pending_items()

    def remove_item(
        self,
        item: InboxItem,
    ) -> None:
        # Source-neutral lifecycle semantics: a durable inbox row is processed,
        # not physically deleted.
        self.repository.mark_processed(
            item.source_item_id
        )
