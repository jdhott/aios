#!/usr/bin/env python3
from datetime import datetime, timedelta, timezone

from aios.ingestion.models import InboxItem
from aios.ingestion import notion_source

def main():
    now = datetime.now(timezone.utc)

    page_children = {
        "brain-dump-page": [
            {"id": "empty-sync", "type": "synced_block"},
            {"id": "live-sync", "type": "synced_block"},
        ],
        "empty-sync": [],
        "live-sync": [
            {
                "id": "task-1",
                "type": "bulleted_list_item",
                "has_children": True,
                "last_edited_time": (
                    now - timedelta(minutes=5)
                ).isoformat(),
                "_text": "Preserve tomatoes",
            },
            {
                "id": "task-2",
                "type": "paragraph",
                "has_children": False,
                "last_edited_time": (
                    now - timedelta(seconds=5)
                ).isoformat(),
                "_text": "Still typing this",
            },
        ],
        "task-1": [
            {
                "id": "note-1",
                "type": "paragraph",
                "_text": "Use pressure canner",
            }
        ],
    }

    summary = {}

    def get_block_children(block_id):
        return page_children.get(block_id, [])

    def get_block_text(block):
        return block.get("_text", "")

    def increment_summary(key, amount=1):
        summary[key] = summary.get(key, 0) + amount

    notion_source.configure_notion_source(
        {
            "get_block_children": get_block_children,
            "get_block_text": get_block_text,
            "increment_summary": increment_summary,
            "RUN_SUMMARY": summary,
            "BRAIN_DUMP_TASK_BLOCK_TYPES": [
                "paragraph",
                "bulleted_list_item",
                "numbered_list_item",
                "to_do",
            ],
            "BRAIN_DUMP_NOTE_BLOCK_TYPES": [
                "paragraph",
                "bulleted_list_item",
                "numbered_list_item",
                "to_do",
            ],
            "ACTIVE_EDIT_GRACE_SECONDS": 30,
            "datetime": datetime,
            "timezone": timezone,
        }
    )

    source = notion_source.NotionInboxSource("brain-dump-page")
    items = source.list_pending_items()

    if len(items) != 1:
        raise RuntimeError(f"Expected one pending item, got {len(items)}")

    item = items[0]

    if not isinstance(item, InboxItem):
        raise RuntimeError("Notion source did not return InboxItem")

    if item.text != "Preserve tomatoes":
        raise RuntimeError(f"Unexpected item text: {item.text}")

    if item.notes != ["Use pressure canner"]:
        raise RuntimeError(f"Unexpected notes: {item.notes}")

    if item.source != "notion":
        raise RuntimeError(f"Unexpected source: {item.source}")

    if item.source_item_id != "task-1":
        raise RuntimeError("source_item_id mapping failed")

    if item.source_container_id != "live-sync":
        raise RuntimeError("source_container_id mapping failed")

    if summary.get("actively_edited_skipped") != 1:
        raise RuntimeError("Active-edit grace behavior was not preserved")

    print("Content-bearing synced block selection: PASS")
    print("InboxItem construction: PASS")
    print("Child note extraction: PASS")
    print("Active-edit grace skip: PASS")
    print("RESULT: NOTION INBOX SOURCE EXTRACTION SMOKE TEST PASSED")

if __name__ == "__main__":
    main()
