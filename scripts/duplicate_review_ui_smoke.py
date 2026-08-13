#!/usr/bin/env python3
from __future__ import annotations

from aios.ingestion.models import InboxItem
from aios.notion import duplicate_review


class FakeResponse:
    def __init__(self, ok=True):
        self.ok = ok
        self.status_code = 200 if ok else 500
        self.text = "fake response"


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
        return FakeResponse(ok=True)


def main():
    fake_requests = FakeRequests()
    summary = {}
    log_events = []

    children_by_id = {
        "source-1": [],
        "source-2": [
            {
                "type": "to_do",
                "to_do": {
                    "checked": True,
                },
                "_text": "🔗 Link to existing task",
            }
        ],
    }

    def get_block_children(block_id):
        return children_by_id.get(
            block_id,
            [],
        )

    def get_block_text(block):
        return block.get("_text", "")

    def get_title(task):
        return task["title"]

    def score_label(score):
        if score >= 0.85:
            return "High"
        if score >= 0.65:
            return "Medium"
        return "Low"

    def increment_summary(key, amount=1):
        summary[key] = (
            summary.get(key, 0)
            + amount
        )

    def log_ai_processing_decision(**kwargs):
        log_events.append(kwargs)
        return True

    duplicate_review.configure_duplicate_review_ui(
        {
            "requests": fake_requests,
            "headers": {
                "Authorization": "fake"
            },
            "get_block_children":
                get_block_children,
            "get_block_text":
                get_block_text,
            "get_title":
                get_title,
            "score_label":
                score_label,
            "increment_summary":
                increment_summary,
            "log_ai_processing_decision":
                log_ai_processing_decision,
            "POSSIBLE_DUPLICATE_HEADER":
                "🔍 Possible duplicate",
            "LINK_EXISTING_COMMAND":
                "🔗 Link to existing task",
            "CREATE_ANYWAY_COMMAND":
                "➕ Create anyway",
            "IGNORE_DUPLICATE_COMMAND":
                "🚫 Ignore duplicate",
        }
    )

    ui = duplicate_review.NotionInboxReviewUI()

    item = InboxItem(
        text="Check generator quote",
        source="notion",
        source_item_id="source-1",
        source_container_id="brain-dump",
        source_type="paragraph",
    )

    rendered = ui.show_possible_duplicate(
        item,
        {"title": "Review generator quote"},
        0.72,
    )

    if rendered is not True:
        raise RuntimeError(
            "Expected duplicate-review UI to render"
        )

    if len(fake_requests.patch_calls) != 1:
        raise RuntimeError(
            "Expected exactly one Notion block PATCH"
        )

    if (
        fake_requests.patch_calls[0]["url"]
        !=
        "https://api.notion.com/v1/blocks/source-1/children"
    ):
        raise RuntimeError(
            "Review UI did not use source_item_id"
        )

    action_item = InboxItem(
        text="Another task",
        source="notion",
        source_item_id="source-2",
        source_container_id="brain-dump",
        source_type="paragraph",
    )

    action = ui.get_possible_duplicate_action(
        action_item
    )

    if action != "🔗 Link to existing task":
        raise RuntimeError(
            f"Unexpected duplicate action: {action}"
        )

    print(
        "Duplicate-review render dispatch: PASS"
    )
    print(
        "Source-neutral source_item_id mapping: PASS"
    )
    print(
        "Duplicate-review selection read: PASS"
    )
    print(
        "No Notion page-property mutation: PASS"
    )
    print(
        "RESULT: DUPLICATE REVIEW UI CUTOVER "
        "SMOKE TEST PASSED"
    )


if __name__ == "__main__":
    main()
