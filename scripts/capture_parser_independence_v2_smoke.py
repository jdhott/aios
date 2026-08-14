#!/usr/bin/env python3
from aios.ingestion import capture_metadata

# Standalone behavior: no configure_capture_metadata() call.
plain = capture_metadata.parse_capture_metadata(
    "need to check kitchen flashlight batteries"
)
assert plain.clean_text == "Check kitchen flashlight batteries", plain.clean_text

todo = capture_metadata.parse_capture_metadata(
    "todo: buy furnace filter"
)
assert todo.clean_text == "Buy furnace filter", todo.clean_text

# Confirm runtime configuration cannot overwrite the canonical cleaner.
original = capture_metadata.clean_task_title

def bad_cleaner(text):
    return "BROKEN"

capture_metadata.configure_capture_metadata({
    "clean_task_title": bad_cleaner,
})

assert capture_metadata.clean_task_title is original
assert capture_metadata.clean_task_title(
    "remember to clean pantry"
) == "Clean pantry"

print("Standalone prefix cleanup: PASS")
print("TODO prefix cleanup: PASS")
print("Canonical cleaner protected from runtime injection: PASS")
print("RESULT: CAPTURE PARSER INDEPENDENCE V2 SMOKE TEST PASSED")
