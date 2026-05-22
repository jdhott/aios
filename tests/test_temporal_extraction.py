
from core.metadata.temporal import extract_temporal_metadata

result = extract_temporal_metadata("Call dentist tomorrow morning")

assert result["cleaned_title"] == "Call dentist"
assert result["due_date"] is not None
assert "tomorrow morning" in result["temporal_tokens_found"]

print(result)
print("Phase 4B consolidation test passed")
