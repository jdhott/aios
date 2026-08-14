#!/usr/bin/env python3
# Intentionally do NOT call configure_capture_metadata().
from aios.ingestion import capture_metadata

plain = capture_metadata.parse_capture_metadata(
    "need to check kitchen flashlight batteries"
)
assert plain.clean_text == "Check kitchen flashlight batteries", plain.clean_text

flagged = capture_metadata.parse_capture_metadata(
    "todo: buy furnace filter - urgent"
)
assert flagged.clean_text == "Buy furnace filter", flagged.clean_text
assert flagged.is_urgent is True

prefixed = capture_metadata.clean_task_title(
    "remember to clean out pantry"
)
assert prefixed == "Clean out pantry", prefixed

separator = capture_metadata.clean_task_title("buy mulch - -")
assert separator == "Buy mulch", separator

print("Standalone parse without runtime configuration: PASS")
print("Common capture prefix cleanup: PASS")
print("Explicit metadata flag cleanup: PASS")
print("Separator cleanup: PASS")
print("RESULT: CAPTURE PARSER INDEPENDENCE SMOKE TEST PASSED")
