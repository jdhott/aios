# Example ingestion migration patch

# OLD

task_name = strip_due_date_phrases(task_name)

if "today" in task_name.lower():
    updates["Due Date"] = today


# NEW

from core.metadata.temporal import (
    extract_temporal_metadata,
)

temporal = extract_temporal_metadata(task_name)

task_name = temporal["cleaned_text"]

if temporal["due_date"]:
    updates["Due Date"] = temporal["due_date"]