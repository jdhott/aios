#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
from aios.notion import archive as archive

class FakeResponse:
    def __init__(self, ok=True, result_id=None):
        self.ok = ok
        self.status_code = 200 if ok else 500
        self.text = "fake response"
        self._result_id = result_id

    def json(self):
        if self._result_id is None:
            return {}
        return {"results": [{"id": self._result_id}]}

class FakeRequests:
    def __init__(self):
        self.patch_calls = []
        self.delete_calls = []

    def patch(self, url, *, headers, json, timeout):
        self.patch_calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeResponse(ok=True, result_id=f"block-{len(self.patch_calls)}")

    def delete(self, url, *, headers, timeout):
        self.delete_calls.append({"url": url, "headers": headers, "timeout": timeout})
        return FakeResponse(ok=True)

def main():
    fake_requests = FakeRequests()
    summary = {}

    def increment_summary(key, amount=1):
        summary[key] = summary.get(key, 0) + amount

    blocks_by_parent = {
        "archive-root": [
            {"id": "note-toggle", "type": "toggle", "_text": "📝 Notes / Reference"}
        ]
    }

    def get_block_children(parent_id):
        return blocks_by_parent.get(parent_id, [])

    def get_block_text(block):
        return block.get("_text", "")

    def get_archive_sibling_parent_id():
        return "brain-dump-parent"

    def notion_text_rich_text(value):
        return [{"type": "text", "text": {"content": str(value)}}]

    archive.configure_archive_module({
        "requests": fake_requests,
        "datetime": datetime,
        "headers": {"Authorization": "fake"},
        "ARCHIVE_TOGGLE_BLOCK_ID": "archive-root",
        "ARCHIVE_PROCESSED_ITEMS": True,
        "DRY_RUN": False,
        "NON_TASK_NOTE_SECTION_HEADER": "📝 Notes / Reference",
        "NON_TASK_IDEA_SECTION_HEADER": "💡 Ideas / Backlog",
        "increment_summary": increment_summary,
        "get_block_children": get_block_children,
        "get_block_text": get_block_text,
        "get_archive_sibling_parent_id": get_archive_sibling_parent_id,
        "notion_text_rich_text": notion_text_rich_text,
    })

    section_id = archive.create_archive_section()
    if section_id != "block-1":
        raise RuntimeError(f"Unexpected archive section id: {section_id}")

    archive.archive_item(
        {"text": "Buy canning jars", "notes": ["Check 500 mL size"]},
        section_id,
        "https://example.invalid/task",
    )

    if summary.get("items_archived") != 1:
        raise RuntimeError("archive_item did not increment items_archived")

    existing = archive.find_child_toggle_by_title(
        "archive-root",
        "📝 Notes / Reference",
    )
    if existing != "note-toggle":
        raise RuntimeError("Existing archive toggle lookup failed")

    archive.delete_original_block("original-block")
    if len(fake_requests.delete_calls) != 1:
        raise RuntimeError("delete_original_block did not issue one block delete")

    if any("/v1/pages/" in call["url"] for call in fake_requests.patch_calls):
        raise RuntimeError("Archive smoke unexpectedly invoked Notion page mutation")

    print("Archive section creation: PASS")
    print("Archive item write: PASS")
    print("Persistent toggle lookup: PASS")
    print("Original block deletion: PASS")
    print("No Notion page-property mutation: PASS")
    print("RESULT: BRAIN DUMP ARCHIVE MODULE CONSOLIDATION SMOKE TEST PASSED")

if __name__ == "__main__":
    main()
