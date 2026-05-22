# FULL PATCH TARGET

# Apply the following integration block into your production file.

# TEMPORAL AUTHORITY PATCH BLOCK
# Replace explicit today/tomorrow reinforcement logic
# with canonical temporal extraction authority.

from core.metadata.temporal import extract_temporal_metadata

# -----------------------------------------------------------------
# Canonical temporal reinforcement parsing
# -----------------------------------------------------------------
temporal = extract_temporal_metadata(source_text)

updates = {}
changed_metadata = {}
preserved_metadata = {
    "Effort": current_effort,
    "Duration": current_duration,
    "Importance": current_importance,
}

if temporal["cleaned_title"]:
    title = temporal["cleaned_title"]

if temporal["due_date"]:
    due_date = temporal["due_date"]

    updates["Due Date"] = {
        "date": {
            "start": due_date.isoformat()
        }
    }

    changed_metadata["Due Date"] = {
        "value": due_date.isoformat(),
        "source": "canonical_temporal_authority",
        "reason": "Canonical temporal extraction",
    }

    print(
        "[Temporal Authority Applied]",
        {
            "title": title,
            "due_date": due_date.isoformat(),
            "signals": temporal.get("signals", []),
        }
    )