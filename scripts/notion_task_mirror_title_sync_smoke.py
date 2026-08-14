#!/usr/bin/env python3
from core.storage.supabase_authority_audit import classify_mutation

title_payload = {
    "properties": {
        "Task Name": {
            "title": [
                {
                    "type": "text",
                    "text": {"content": "Resolved task title"},
                }
            ]
        }
    }
}

broad_payload = {
    "properties": {
        "Task Name": {
            "title": [
                {
                    "type": "text",
                    "text": {"content": "Resolved task title"},
                }
            ],
        },
        "archived": True,
    }
}

category, _ = classify_mutation(
    "PATCH",
    "https://api.notion.com/v1/pages/example",
    title_payload,
)
assert category == "allowed_task_mirror", category

category, _ = classify_mutation(
    "PATCH",
    "https://api.notion.com/v1/pages/example",
    broad_payload,
)
assert category == "unexpected_authoritative", category

category, _ = classify_mutation(
    "DELETE",
    "https://api.notion.com/v1/pages/example",
    None,
)
assert category == "unexpected_authoritative", category

print("Title-only mirror PATCH classification: PASS")
print("Broader page PATCH remains blocked: PASS")
print("Page DELETE remains blocked: PASS")
print("RESULT: NOTION TASK MIRROR TITLE SYNC SMOKE TEST PASSED")
