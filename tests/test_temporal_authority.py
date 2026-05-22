from datetime import datetime, timedelta
from core.metadata.temporal import extract_temporal_metadata

today = datetime.now().date()

result = extract_temporal_metadata(
    "Call dentist tomorrow morning"
)

assert result["cleaned_title"] == "Call dentist"
assert result["due_date"] == today + timedelta(days=1)

print("Temporal authority smoke tests passed")