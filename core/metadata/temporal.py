from __future__ import annotations

import re
from datetime import datetime, timedelta

TEMPORAL_PATTERNS = [
    r"\btoday\b",
    r"\btonight\b",
    r"\btomorrow\b",
    r"\btomorrow morning\b",
    r"\btomorrow afternoon\b",
    r"\btomorrow evening\b",
]

TEMPORAL_REGEX = re.compile(
    "|".join(TEMPORAL_PATTERNS),
    re.IGNORECASE,
)

def strip_temporal_language(text):
    if not text:
        return text

    cleaned = TEMPORAL_REGEX.sub("", text)
    cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned.strip(" -")

def extract_temporal_metadata(text):
    normalized = (text or "").lower()

    due_date = None

    if "tomorrow" in normalized:
        due_date = datetime.now().date() + timedelta(days=1)

    elif "today" in normalized or "tonight" in normalized:
        due_date = datetime.now().date()

    cleaned_title = strip_temporal_language(text)

    metadata = {
        "raw_text": text,
        "cleaned_title": cleaned_title,
        "due_date": due_date,
    }

    print("[Temporal Authority]", metadata)

    return metadata