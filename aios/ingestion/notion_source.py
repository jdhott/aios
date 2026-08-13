from __future__ import annotations

from aios.ingestion.models import InboxItem
from aios.ingestion.source import InboxSource

def configure_notion_source(namespace):
    globals().update(namespace)

class NotionInboxSource:
    def __init__(self, page_id):
        self.page_id = page_id

    def list_pending_items(self) -> list[InboxItem]:
        return extract_brain_dump_items(self.page_id)

    def remove_item(self, item: InboxItem) -> None:
        """Remove the processed source block from the Notion Brain Dump."""
        delete_original_block(item.source_item_id)

def find_first_synced_block(parent_block_id):
    """Return the synced block that actually contains Brain Dump task items.

    Historically AIOS selected the first synced block on the page. That is
    fragile when Notion leaves an empty/stale synced block ahead of the real
    Brain Dump source. Prefer a synced block with at least one supported,
    non-empty task block; fall back to the first synced block for compatibility.
    """
    blocks = get_block_children(parent_block_id)
    synced_blocks = [block for block in blocks if block.get("type") == "synced_block"]

    if not synced_blocks:
        return None

    first_id = synced_blocks[0].get("id")
    print(f"Brain Dump synced blocks found: {len(synced_blocks)}")

    for index, block in enumerate(synced_blocks, start=1):
        block_id = block.get("id")
        if not block_id:
            continue
        children = get_block_children(block_id)
        candidate_count = 0
        for child in children:
            if child.get("type") not in BRAIN_DUMP_TASK_BLOCK_TYPES:
                continue
            if get_block_text(child):
                candidate_count += 1
        print(f"  Synced block {index}: {block_id} — {candidate_count} candidate item(s)")
        if candidate_count:
            if block_id != first_id:
                print(f"Brain Dump source fallback: using content-bearing synced block {block_id}")
            return block_id

    print("WARNING: no synced block on the Brain Dump page contains eligible task text")
    return first_id


def get_block_age_seconds(block):
    """Return seconds since this block was last edited."""
    last_edited = block.get("last_edited_time")

    if not last_edited:
        return None

    try:
        edited_dt = datetime.fromisoformat(
            last_edited.replace("Z", "+00:00")
        )

        now = datetime.now(timezone.utc)

        return (now - edited_dt).total_seconds()

    except Exception as e:
        print(f"WARNING parsing block edit time: {e}")
        return None


def extract_note_texts_from_block(block):
    """Return direct child block text as informational notes for one inbox item.

    Brain Dump convention:
    - top-level block = task title
    - direct child blocks = notes/context for that task

    Notes are deliberately not used for classification, duplicate detection,
    Quick Win or breakdown decisions in this V1.
    """
    if not block.get("has_children"):
        return []

    notes = []

    for child in get_block_children(block["id"]):
        if child.get("type") not in BRAIN_DUMP_NOTE_BLOCK_TYPES:
            continue

        note_text = get_block_text(child)
        if note_text:
            notes.append(note_text)

    return notes


def extract_brain_dump_items(BRAIN_DUMP_PAGE_ID):
    synced_block_id = find_first_synced_block(BRAIN_DUMP_PAGE_ID)

    if not synced_block_id:
        print("No synced block found on Brain Dump page")
        return []

    print("Using synced block:", synced_block_id)

    inbox_items = []

    blocks = get_block_children(synced_block_id)

    for block in blocks:
        block_type = block.get("type")
        block_id = block.get("id")

        if block_type not in BRAIN_DUMP_TASK_BLOCK_TYPES:
            continue

        text = get_block_text(block)

        if not text:
            continue

        age_seconds = get_block_age_seconds(block)

        if (
            age_seconds is not None
            and age_seconds < ACTIVE_EDIT_GRACE_SECONDS
        ):
            increment_summary("actively_edited_skipped")

            print(
                f"Skipping actively edited block "
                f"({int(age_seconds)}s old): {text}"
            )

            continue

        notes = extract_note_texts_from_block(block)

        inbox_items.append(
            InboxItem(
                text=text,
                notes=notes,
                source="notion",
                source_item_id=block_id,
                source_container_id=synced_block_id,
                source_type=block_type,
            )
        )

        if notes:
            print(f"Extracted notes for: {text}")
            for note in notes:
                print(f"  - {note}")

    print(f"Extracted {len(inbox_items)} brain dump item(s)")

    skipped = RUN_SUMMARY.get("actively_edited_skipped", 0)

    if skipped:
        print(f"Skipped {skipped} actively edited block(s)")

    RUN_SUMMARY["inbox_extracted"] = len(inbox_items)

    return inbox_items


