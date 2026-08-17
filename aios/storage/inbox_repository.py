from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from aios.ingestion.models import InboxItem
from aios.ingestion.capture_metadata import (
    CaptureMetadata,
    has_meaningful_capture_text,
)
from aios.storage.supabase_store import SupabaseStore


class InboxRepository:
    """Supabase persistence layer for the source-neutral AIOS inbox."""

    PAGE_SIZE = 1000

    def __init__(self, store: SupabaseStore):
        self.store = store

    def row_to_inbox_item(
        self,
        row: dict[str, Any],
    ) -> InboxItem:
        """
        Convert one Supabase inbox row to the AIOS source-neutral model.

        For this adapter, InboxItem.source_item_id is the inbox row UUID because
        that is the identity used by lifecycle methods. Any original external
        source ID remains in the Supabase row's source_item_id/source_metadata.
        """
        source_metadata = row.get("source_metadata") or {}

        return InboxItem(
            text=row.get("text") or "",
            notes=list(row.get("notes") or []),
            source=row.get("source") or "brain_dump",
            source_item_id=str(
                row.get("source_item_id")
                or row["id"]
            ),
            source_container_id=source_metadata.get(
                "source_container_id"
            ),
            source_type=source_metadata.get(
                "source_type"
            ) or "inbox_item",
            inbox_row_id=str(row["id"]),
        )

    def get_pending_rows(
        self,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        start = 0

        while True:
            response = (
                self.store.client
                .table("inbox_items")
                .select("*")
                .eq("status", "pending")
                .order("created_at")
                .range(
                    start,
                    start + self.PAGE_SIZE - 1,
                )
                .execute()
            )

            batch = response.data or []
            rows.extend(batch)

            if len(batch) < self.PAGE_SIZE:
                break

            start += self.PAGE_SIZE

        return rows

    def get_pending_items(
        self,
    ) -> list[InboxItem]:
        rows = self.get_pending_rows()

        native_rows = [
            row
            for row in rows
            if not bool(
                (row.get("source_metadata") or {})
                .get("shadow")
            )
        ]

        skipped = len(rows) - len(native_rows)
        if skipped:
            print(
                "[Supabase Inbox] "
                f"Skipped {skipped} shadow row(s) from capture ingestion"
            )

        return [
            self.row_to_inbox_item(row)
            for row in native_rows
        ]


    def get_by_source_identity(
        self,
        *,
        source: str,
        source_item_id: str,
    ) -> Optional[dict[str, Any]]:
        response = (
            self.store.client
            .table("inbox_items")
            .select("*")
            .eq("source", source)
            .eq("source_item_id", source_item_id)
            .limit(1)
            .execute()
        )

        rows = response.data or []
        return rows[0] if rows else None

    def get_review_rows_for_item(
        self,
        item: InboxItem,
    ) -> list[dict[str, Any]]:
        """Return inbox rows that may own reviews for this item.

        Supabase-native inbox rows are authoritative. A source-identity
        shadow row is also returned when present for compatibility with
        reviews created before native review authority.
        """
        rows: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        if item.inbox_row_id:
            native = self.get_row(
                str(item.inbox_row_id)
            )

            if native:
                row_id = str(native.get("id") or "")
                if row_id:
                    seen_ids.add(row_id)
                rows.append(native)

        if item.source and item.source_item_id:
            legacy = self.get_by_source_identity(
                source=item.source,
                source_item_id=item.source_item_id,
            )

            if legacy:
                row_id = str(legacy.get("id") or "")

                if row_id not in seen_ids:
                    rows.append(legacy)

        return rows


    def get_review_row_for_item(
        self,
        item: InboxItem,
    ) -> dict[str, Any]:
        """Return the authoritative row to own a newly created review."""
        rows = self.get_review_rows_for_item(item)

        if rows:
            # Native row is returned first when available.
            return rows[0]

        # Legacy/Notion-origin items still require a shadow row.
        return self.get_or_create_shadow_item(item)


    def get_or_create_shadow_item(
        self,
        item: InboxItem,
    ) -> dict[str, Any]:
        if not item.source:
            raise ValueError("Shadow inbox item requires a source.")

        if not item.source_item_id:
            raise ValueError(
                "Shadow inbox item requires source_item_id."
            )

        existing = self.get_by_source_identity(
            source=item.source,
            source_item_id=item.source_item_id,
        )

        if existing:
            return existing

        source_metadata = {
            "shadow": True,
            "source_container_id":
                item.source_container_id,
            "source_type":
                item.source_type,
        }

        try:
            return self.create_item(
                text=item.text,
                notes=list(item.notes or []),
                source=item.source,
                source_item_id=item.source_item_id,
                source_metadata=source_metadata,
            )
        except Exception:
            existing = self.get_by_source_identity(
                source=item.source,
                source_item_id=item.source_item_id,
            )

            if existing:
                return existing

            raise

    def get_row(
        self,
        inbox_id: str,
    ) -> Optional[dict[str, Any]]:
        response = (
            self.store.client
            .table("inbox_items")
            .select("*")
            .eq("id", inbox_id)
            .limit(1)
            .execute()
        )

        rows = response.data or []
        return rows[0] if rows else None

    def create_item(
        self,
        *,
        text: str,
        notes: Optional[list[str]] = None,
        source: str = "brain_dump",
        source_item_id: Optional[str] = None,
        source_metadata: Optional[dict[str, Any]] = None,
        capture_metadata: Optional[CaptureMetadata] = None,
    ) -> dict[str, Any]:
        payload = {
            "text": text,
            "notes": list(notes or []),
            "source": source,
            "source_item_id": source_item_id,
            "source_metadata": source_metadata or {},
            "status": "pending",
            "clean_text": capture_metadata.clean_text if capture_metadata else None,
            "due_date": (
                capture_metadata.due_date.isoformat()
                if capture_metadata and capture_metadata.due_date
                else None
            ),
            "project_hint": capture_metadata.project_hint if capture_metadata else None,
            "is_urgent": capture_metadata.is_urgent if capture_metadata else False,
            "is_important": capture_metadata.is_important if capture_metadata else False,
            "is_just_do_it": capture_metadata.is_jdi if capture_metadata else False,
        }

        response = (
            self.store.client
            .table("inbox_items")
            .insert(payload)
            .execute()
        )

        if not (response.data or []):
            raise RuntimeError(
                "Failed to create Supabase inbox item."
            )

        return response.data[0]


    def create_brain_dump_item(
        self,
        *,
        raw_text: str,
        notes: Optional[list[str]] = None,
        parser,
        source_metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        if not has_meaningful_capture_text(raw_text):
            raise ValueError(
                "Brain Dump item contains no meaningful task text."
            )

        capture = parser(raw_text)
        if not isinstance(capture, CaptureMetadata):
            raise TypeError("Brain Dump parser must return CaptureMetadata")

        return self.create_item(
            text=raw_text,
            notes=notes,
            source="brain_dump",
            source_metadata=source_metadata,
            capture_metadata=capture,
        )

    def mark_processed(
        self,
        inbox_id: str,
    ) -> dict[str, Any]:
        response = (
            self.store.client
            .table("inbox_items")
            .update(
                {
                    "status": "processed",
                    "processed_at": (
                        datetime.now(timezone.utc)
                        .isoformat()
                    ),
                }
            )
            .eq("id", inbox_id)
            .execute()
        )

        if not (response.data or []):
            raise RuntimeError(
                f"Failed to mark inbox item processed: {inbox_id}"
            )

        return response.data[0]

    def delete_item(
        self,
        inbox_id: str,
    ) -> None:
        (
            self.store.client
            .table("inbox_items")
            .delete()
            .eq("id", inbox_id)
            .execute()
        )
