"""Notion Brain Dump archive / presentation helpers for AIOS.

This module owns the Notion block-level archive behavior extracted from
run_aios.py. configure_archive_module() injects the already-initialized runtime
dependencies supplied by run_aios.py so this refactor changes code ownership,
not behavior or persistence authority.
"""

def configure_archive_module(namespace):
    """Provide run_aios runtime globals used by archive helpers."""
    globals().update(namespace)


def create_archive_section():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    payload = {
        "children": [
            {
                "object": "block",
                "type": "toggle",
                "toggle": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": timestamp}
                        }
                    ]
                }
            }
        ]
    }

    print(
        "[Metadata PATCH Payload]",
        )
    response = requests.patch(
        f"https://api.notion.com/v1/blocks/{ARCHIVE_TOGGLE_BLOCK_ID}/children",
        headers=headers,
        json=payload,
        timeout=30,
    )

    if not response.ok:
        increment_summary("errors")
        print("ERROR creating archive section")
        print(response.status_code, response.text)
        return None

    return response.json()["results"][0]["id"]


def archive_item(item, archive_section_id, task_url=None):
    text = item["text"].strip()

    if task_url:
        text = f"{text} → {task_url}"

    notes = item.get("notes") or []
    if notes:
        notes_text = "\n".join(f"  - {note}" for note in notes)
        text = f"{text}\nNotes:\n{notes_text}"

    payload = {
        "children": [
            {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": text}
                        }
                    ]
                }
            }
        ]
    }

    response = requests.patch(
        f"https://api.notion.com/v1/blocks/{archive_section_id}/children",
        headers=headers,
        json=payload,
        timeout=30,
    )

    if response.ok:
        increment_summary("items_archived")
        print("Archived item:", item["text"])
    else:
        increment_summary("errors")
        print("ERROR archiving item:", item["text"])
        print(response.status_code, response.text)


def append_archive_toggle(parent_block_id, title):
    """Append a toggle block under a parent block and return its ID."""
    if not parent_block_id or not title:
        return None

    payload = {
        "children": [
            {
                "object": "block",
                "type": "toggle",
                "toggle": {
                    "rich_text": notion_text_rich_text(title) if "notion_text_rich_text" in globals() else [
                        {"type": "text", "text": {"content": str(title)[:1900]}}
                    ]
                },
            }
        ]
    }

    response = requests.patch(
        f"https://api.notion.com/v1/blocks/{parent_block_id}/children",
        headers=headers,
        json=payload,
        timeout=30,
    )

    if response.ok:
        return response.json()["results"][0]["id"]

    increment_summary("errors")
    print("ERROR creating archive subsection:", title)
    print(response.status_code, response.text)
    return None


def find_child_toggle_by_title(parent_block_id, title):
    """Return the first direct child toggle ID with this title, if it exists."""
    if not parent_block_id or not title:
        return None

    for block in get_block_children(parent_block_id):
        if block.get("type") != "toggle":
            continue
        if get_block_text(block).strip() == title:
            return block.get("id")

    return None


def get_or_create_archive_toggle(parent_block_id, title):
    """Find or create a persistent toggle under the supplied parent container."""
    existing_id = find_child_toggle_by_title(parent_block_id, title)
    if existing_id:
        return existing_id

    new_id = append_archive_toggle(parent_block_id, title)
    if new_id:
        print("Created archive toggle:", title)
    return new_id


def archive_non_task_item(item, archive_section_id, section_header, summary_key, label):
    """Archive a non-task Brain Dump item under a persistent sibling toggle.

    Notes and ideas should not be hidden inside the timestamped run archive.
    They are appended under stable side-channel toggles at the same level as
    the main Archive toggle:
    - 📝 Notes / Reference
    - 💡 Ideas / Backlog
    """
    if DRY_RUN:
        print(f"[DRY RUN] Would route non-task {label}: {item['text']}")
        return

    if not ARCHIVE_PROCESSED_ITEMS:
        print(f"[NO ARCHIVE] Leaving non-task {label} in place: {item['text']}")
        return

    destination_parent_id = get_archive_sibling_parent_id()
    destination_id = get_or_create_archive_toggle(destination_parent_id, section_header)
    if not destination_id:
        # Conservative fallback: use this run's archive section if persistent
        # sibling toggle creation failed, so the item is not lost.
        destination_id = archive_section_id

    if not destination_id:
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    item_for_archive = dict(item)
    item_for_archive["text"] = f"{timestamp} — {item['text']}"

    archive_item(item_for_archive, destination_id)
    delete_original_block(item["block_id"])
    increment_summary(summary_key)
    print(f"Routed non-task {label}:", item["text"])


def archive_non_task_note_item(item, archive_section_id):
    """Archive a clear informational non-task under Notes / Reference."""
    return archive_non_task_item(
        item,
        archive_section_id,
        NON_TASK_NOTE_SECTION_HEADER,
        "non_task_notes_routed",
        "note",
    )


def archive_non_task_idea_item(item, archive_section_id):
    """Archive a clear idea/backlog non-task under Ideas / Backlog."""
    return archive_non_task_item(
        item,
        archive_section_id,
        NON_TASK_IDEA_SECTION_HEADER,
        "non_task_ideas_routed",
        "idea",
    )


def delete_original_block(block_id):
    response = requests.delete(
        f"https://api.notion.com/v1/blocks/{block_id}",
        headers=headers,
        timeout=30,
    )

    if response.ok:
        print("Removed original block:", block_id)
    else:
        increment_summary("errors")
        print("ERROR removing original block:", block_id)
        print(response.status_code, response.text)


def trim_archive_runs(keep=5):
    children = get_block_children(ARCHIVE_TOGGLE_BLOCK_ID)

    persistent_archive_toggles = {
        NON_TASK_NOTE_SECTION_HEADER,
        NON_TASK_IDEA_SECTION_HEADER,
        NON_TASK_REVIEW_SECTION_HEADER,
    }

    archive_runs = [
        block for block in children
        if block.get("type") == "toggle"
        and get_block_text(block).strip() not in persistent_archive_toggles
    ]

    if len(archive_runs) <= keep:
        print(f"Archive trim skipped: {len(archive_runs)} timestamped run(s)")
        return

    old_runs = archive_runs[:-keep]

    for block in old_runs:
        delete_original_block(block["id"])

    increment_summary("archive_runs_trimmed", len(old_runs))
    print(f"Trimmed {len(old_runs)} old archive run(s)")


