#!/usr/bin/env python3
from aios.ingestion.models import InboxItem
from aios.notion import duplicate_review
item=InboxItem(text="Supabase possible duplicate",notes=[],source="brain_dump",source_item_id="row-uuid",source_type="inbox_item")
ui=duplicate_review.NotionInboxReviewUI()
assert ui.show_possible_duplicate(item,{"id":"candidate"},0.82) is False
assert ui.get_possible_duplicate_action(item) is None
print("Supabase-origin Notion presentation skip: PASS")
print("Supabase-origin Notion action read skip: PASS")
print("RESULT: APP SERVICE BOUNDARY PHASE 1.2 SMOKE TEST PASSED")
