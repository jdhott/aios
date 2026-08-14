#!/usr/bin/env python3
"""Offline smoke for duplicate-review runtime dependencies and source identity."""
from __future__ import annotations

from aios.ingestion.models import InboxItem
from aios.notion import duplicate_review


class FakeResponse:
    ok = True
    status_code = 200
    text = "OK"


class FakeRequests:
    def __init__(self):
        self.patch_calls = []

    def patch(
        self,
        url,
        *,
        headers,
        json,
        timeout,
    ):
        self.patch_calls.append(
            {
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": timeout,
            }
        )
        return FakeResponse()


def main() -> None:
    requests = FakeRequests()
    summary = {}

    def increment_summary(key, amount=1):
        summary[key] = summary.get(key, 0) + amount

    def get_block_children(block_id):
        # No pre-existing review UI.
        return []

    def get_block_text(block):
        return ""

    def get_title(task):
        return task["title"]

    def score_label(score):
        if score >= 0.90:
            return "High"
        if score >= 0.75:
            return "Medium"
        return "Low"

    def log_ai_processing_decision(**kwargs):
        return True

    duplicate_review.configure_duplicate_review_ui(
        {
            "requests": requests,
            "headers": {"Authorization": "test"},
            "get_block_children": get_block_children,
            "get_block_text": get_block_text,
            "get_title": get_title,
            "score_label": score_label,
            "increment_summary": increment_summary,
            "log_ai_processing_decision": log_ai_processing_decision,
            "POSSIBLE_DUPLICATE_HEADER": "Possible duplicate",
            "LINK_EXISTING_COMMAND": "Use existing",
            "CREATE_ANYWAY_COMMAND": "Create anyway",
            "IGNORE_DUPLICATE_COMMAND": "Ignore",
        }
    )

    item = InboxItem(
        text="Check generator quote",
        notes=[],
        source="notion",
        source_item_id="notion-block-123",
        source_container_id="brain-dump-sync",
        source_type="paragraph",
    )

    result = duplicate_review.append_possible_duplicate_blocks(
        item,
        {"title": "Review the generator quote"},
        0.77,
    )

    if result is not True:
        raise RuntimeError(
            "Duplicate review renderer did not report success."
        )

    if len(requests.patch_calls) != 1:
        raise RuntimeError(
            "Expected exactly one Notion PATCH."
        )

    call = requests.patch_calls[0]

    expected_url = (
        "https://api.notion.com/v1/blocks/"
        "notion-block-123/children"
    )

    if call["url"] != expected_url:
        raise RuntimeError(
            f"Wrong source identity in PATCH URL: {call['url']}"
        )

    rendered = str(call["json"])
    if "Medium" not in rendered or "0.77" not in rendered:
        raise RuntimeError(
            "score_label dependency was not used correctly."
        )

    print("Late score_label dependency availability: PASS")
    print("Source-neutral source_item_id PATCH target: PASS")
    print("Possible-duplicate UI render: PASS")
    print("No legacy block_id dependency: PASS")
    print(
        "RESULT: DUPLICATE REVIEW RUNTIME DEPENDENCY FIX "
        "SMOKE TEST PASSED"
    )


if __name__ == "__main__":
    main()
