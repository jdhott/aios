from __future__ import annotations

from aios.ingestion.models import InboxItem
from aios.review.interface import InboxReviewUI


def configure_duplicate_review_ui(namespace):
    globals().update(namespace)


SOURCE_AWARE_DUPLICATE_REVIEW_VERSION = "app-service-boundary-v1-phase1.2"

class NotionInboxReviewUI:
    def show_possible_duplicate(
        self,
        item: InboxItem,
        matched_task,
        score: float,
    ) -> bool:
        if item.source != "notion":
            print(
                "[Inbox Review UI] Skipping Notion duplicate presentation for "
                f"{item.source_type or item.source} source: {item.text}"
            )
            return False

        return append_possible_duplicate_blocks(
            item,
            matched_task,
            score,
        )

    def get_possible_duplicate_action(
        self,
        item: InboxItem,
    ) -> str | None:
        if item.source != "notion":
            return None

        return get_checked_possible_duplicate_action(
            item
        )


def has_possible_duplicate_blocks(block_id):
    children = get_block_children(block_id)

    duplicate_headers = {
        POSSIBLE_DUPLICATE_HEADER,
        "🔍 Possible related task (low confidence)",
    }

    for block in children:
        if get_block_text(block) in duplicate_headers:
            return True

    return False


def append_possible_duplicate_blocks(item, matched_task, score):
    if has_possible_duplicate_blocks(item.source_item_id):
        return

    existing_title = get_title(matched_task)

    confidence = score_label(score)

    header = POSSIBLE_DUPLICATE_HEADER
    if confidence == "Low":
        header = "🔍 Possible related task (low confidence)"

    children = [
        {
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"type": "text", "text": {"content": header}}]
            },
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": f"Original: {item['text']}"}}]
            },
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": f"Possible match: {existing_title}"}}]
            },
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": f"Confidence: {score_label(score)} ({score:.2f})"}}]
            },
        },
        {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"type": "text", "text": {"content": LINK_EXISTING_COMMAND}}],
                "checked": False,
            },
        },
        {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"type": "text", "text": {"content": CREATE_ANYWAY_COMMAND}}],
                "checked": False,
            },
        },
        {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"type": "text", "text": {"content": IGNORE_DUPLICATE_COMMAND}}],
                "checked": False,
            },
        },
    ]

    response = requests.patch(
        f"https://api.notion.com/v1/blocks/{item.source_item_id}/children",
        headers=headers,
        json={"children": children},
        timeout=30,
    )

    if response.ok:
        increment_summary("possible_duplicate_blocks_added")
        print("Added possible duplicate review blocks:", item["text"])
        log_ai_processing_decision(
            original=item["text"],
            final_task=existing_title,
            action="Duplicate",
            reason=f"Possible duplicate match requires review; confidence {score_label(score)} ({score:.2f}).",
            review_needed=True,
            confidence=score,
        )
        return True

    increment_summary("errors")
    print("ERROR adding possible duplicate review blocks")
    print(response.status_code, response.text)
    return False


def get_checked_possible_duplicate_action(item):
    children = get_block_children(item.source_item_id)

    for block in children:
        if block.get("type") != "to_do":
            continue

        todo = block.get("to_do", {})

        if not todo.get("checked"):
            continue

        text = get_block_text(block)

        if text in [
            LINK_EXISTING_COMMAND,
            CREATE_ANYWAY_COMMAND,
            IGNORE_DUPLICATE_COMMAND,
        ]:
            return text

    return None


