
from core.metadata.temporal import extract_temporal_metadata

result = extract_temporal_metadata(
    "Call dentist tomorrow morning"
)

assert result["cleaned_title"] == "Call dentist"
assert result["due_date"] is not None

print(result)
print("Temporal authority smoke test passed")
