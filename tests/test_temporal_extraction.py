from core.metadata.temporal import (
    extract_temporal_metadata,
    cleanup_temporal_tokens,
)

print(cleanup_temporal_tokens("Call dentist tomorrow morning"))

result = extract_temporal_metadata(
    "Call dentist tomorrow morning"
)

assert result["due_date"] is not None

print(result)
print("Temporal authority smoke test passed")