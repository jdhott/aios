#!/usr/bin/env python3
from types import SimpleNamespace
import aios.api.app as api_module

class Repo:
    def __init__(self, rows):
        self.rows = rows
        self.processed = []

    def get_row(self, inbox_id):
        return self.rows.get(inbox_id)

    def mark_processed(self, inbox_id):
        self.processed.append(inbox_id)

def run(rows, inbox_item_id):
    repo = Repo(rows)
    api_module._inbox_repository = lambda: repo
    api_module._mark_review_inbox_processed(
        SimpleNamespace(inbox_item_id=inbox_item_id)
    )
    return repo.processed

assert run(
    {"native": {"source_item_id": None, "source_metadata": {}}},
    "native",
) == ["native"]

assert run(
    {"shadow": {"source_item_id": "", "source_metadata": {"shadow": True}}},
    "shadow",
) == ["shadow"]

assert run(
    {"shadow": {"source_item_id": "missing", "source_metadata": {"shadow": True}}},
    "shadow",
) == ["shadow"]

assert run(
    {"shadow": {"source_item_id": "shadow", "source_metadata": {"shadow": True}}},
    "shadow",
) == ["shadow"]

print("Non-shadow row lifecycle: PASS")
print("Missing origin identity fails safe: PASS")
print("Missing origin row fails safe: PASS")
print("Self-reference fails safe: PASS")
print("RESULT: CLOUD WORKFLOW LIFECYCLE FIX V1.1 EDGE TEST PASSED")
