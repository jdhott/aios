#!/usr/bin/env python3
from aios.ingestion.models import InboxItem

def main():
    item = InboxItem(
        text="Preserve tomatoes",
        notes=["Use pressure canner"],
        source="notion",
        source_item_id="block-123",
        source_container_id="synced-456",
        source_type="bulleted_list_item",
    )

    if item["text"] != "Preserve tomatoes":
        raise RuntimeError("Legacy text access failed")

    if item.get("notes") != ["Use pressure canner"]:
        raise RuntimeError("Legacy notes access failed")

    if item["block_id"] != "block-123":
        raise RuntimeError("Legacy block_id compatibility failed")

    if item["parent_block_id"] != "synced-456":
        raise RuntimeError("Legacy parent_block_id compatibility failed")

    legacy = dict(item)
    expected = {
        "text",
        "notes",
        "block_id",
        "block_type",
        "parent_block_id",
    }

    if set(legacy) != expected:
        raise RuntimeError(f"dict(item) shape changed unexpectedly: {legacy}")

    neutral = item.to_source_neutral_dict()

    if neutral["source"] != "notion":
        raise RuntimeError("Source-neutral source missing")

    if neutral["source_item_id"] != "block-123":
        raise RuntimeError("Source-neutral source_item_id missing")

    print("Legacy item['text'] access: PASS")
    print("Legacy item.get('notes') access: PASS")
    print("Legacy block_id compatibility: PASS")
    print("Legacy dict(item) compatibility: PASS")
    print("Source-neutral representation: PASS")
    print("RESULT: INBOX ITEM MODEL CUTOVER SMOKE TEST PASSED")

if __name__ == "__main__":
    main()
