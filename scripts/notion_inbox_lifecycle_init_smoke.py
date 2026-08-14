#!/usr/bin/env python3
from aios.ingestion import notion_source

def main():
    calls = []

    def fake_delete(block_id):
        calls.append(block_id)

    # First configure without delete_original_block to mirror the problematic
    # early startup state.
    notion_source.configure_notion_source({})

    # Then refresh after lifecycle helpers are available.
    notion_source.configure_notion_source(
        {"delete_original_block": fake_delete}
    )

    source = notion_source.NotionInboxSource("brain-dump-page")

    class FakeItem:
        source_item_id = "notion-block-123"

    source.remove_item(FakeItem())

    if calls != ["notion-block-123"]:
        raise RuntimeError(
            f"Expected refreshed delete_original_block call; got {calls}"
        )

    print("Late lifecycle dependency refresh: PASS")
    print("NotionInboxSource.remove_item dispatch: PASS")
    print("delete_original_block availability: PASS")
    print("RESULT: NOTION INBOX LIFECYCLE INIT FIX SMOKE TEST PASSED")

if __name__ == "__main__":
    main()
