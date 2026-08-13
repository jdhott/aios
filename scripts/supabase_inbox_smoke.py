#!/usr/bin/env python3
"""
Controlled live smoke test for the inactive Supabase Inbox path.

This test:
1. Creates one uniquely tagged temporary inbox row.
2. Reads it through SupabaseInboxSource as InboxItem.
3. Calls remove_item(), which must mark it processed.
4. Verifies the processed state.
5. Deletes the temporary row in a finally block.

It does not touch Notion, tasks, projects, or production Brain Dump items.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from dotenv import load_dotenv, find_dotenv

from aios.ingestion.supabase_source import (
    SupabaseInboxSource,
)
from aios.storage.inbox_repository import (
    InboxRepository,
)
from aios.storage.supabase_store import (
    SupabaseStore,
)


def main() -> None:
    load_dotenv(
        find_dotenv() or ".env",
        override=True,
    )

    store = SupabaseStore()
    repository = InboxRepository(store)
    source = SupabaseInboxSource(repository)

    marker = (
        "AIOS_SUPABASE_INBOX_SMOKE_"
        + uuid4().hex
    )

    created_id = None

    try:
        row = repository.create_item(
            text=marker,
            notes=[
                "Temporary controlled inbox smoke test"
            ],
            source="brain_dump",
            source_metadata={
                "test": True,
                "created_by":
                    "scripts.supabase_inbox_smoke",
                "created_at": (
                    datetime.now(timezone.utc)
                    .isoformat()
                ),
            },
        )

        created_id = str(row["id"])

        pending = source.list_pending_items()

        matches = [
            item
            for item in pending
            if item.source_item_id == created_id
        ]

        if len(matches) != 1:
            raise RuntimeError(
                "Temporary inbox row was not returned "
                "through SupabaseInboxSource."
            )

        item = matches[0]

        if item.text != marker:
            raise RuntimeError(
                "InboxItem text mapping failed."
            )

        if item.source != "brain_dump":
            raise RuntimeError(
                "InboxItem source mapping failed."
            )

        if item.notes != [
            "Temporary controlled inbox smoke test"
        ]:
            raise RuntimeError(
                "InboxItem notes mapping failed."
            )

        source.remove_item(item)

        processed = repository.get_row(
            created_id
        )

        if not processed:
            raise RuntimeError(
                "Temporary inbox row disappeared instead "
                "of being marked processed."
            )

        if processed.get("status") != "processed":
            raise RuntimeError(
                "remove_item() did not mark row processed."
            )

        if not processed.get("processed_at"):
            raise RuntimeError(
                "processed_at was not set."
            )

        print("Temporary inbox insert: PASS")
        print("SupabaseInboxSource read: PASS")
        print("InboxItem mapping: PASS")
        print("remove_item marks processed: PASS")
        print("Durable processed row verified: PASS")
        print(
            "RESULT: SUPABASE INBOX POC "
            "SMOKE TEST PASSED"
        )

    finally:
        if created_id:
            repository.delete_item(
                created_id
            )

            if repository.get_row(
                created_id
            ) is not None:
                raise RuntimeError(
                    "Smoke cleanup failed: temporary inbox "
                    "row still exists."
                )

            print(
                "Temporary inbox row cleanup: PASS"
            )


if __name__ == "__main__":
    main()
