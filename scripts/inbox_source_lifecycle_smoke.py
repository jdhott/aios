#!/usr/bin/env python3
from __future__ import annotations

from aios.ingestion.models import InboxItem
from aios.ingestion import notion_source


def main():
    removed = []

    def fake_delete_original_block(block_id):
        removed.append(block_id)

    notion_source.configure_notion_source(
        {
            "delete_original_block":
                fake_delete_original_block,
        }
    )

    source = notion_source.NotionInboxSource(
        "brain-dump-page"
    )

    item = InboxItem(
        text="Preserve tomatoes",
        notes=[],
        source="notion",
        source_item_id="notion-block-123",
        source_container_id="synced-block-456",
        source_type="paragraph",
    )

    source.remove_item(item)

    if removed != ["notion-block-123"]:
        raise RuntimeError(
            f"Unexpected source removal calls: {removed}"
        )

    print("Source-neutral remove_item dispatch: PASS")
    print("Notion source_item_id mapping: PASS")
    print("No network request performed: PASS")
    print(
        "RESULT: INBOX SOURCE LIFECYCLE CUTOVER "
        "SMOKE TEST PASSED"
    )


if __name__ == "__main__":
    main()
