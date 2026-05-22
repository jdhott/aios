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

def cleanup_temporal_tokens(text):
    if not text:
        return ""

    cleaned = TEMPORAL_REGEX.sub("", text)
    cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned.strip(" -")

def strip_temporal_language(text):
    return cleanup_temporal_tokens(text)

def extract_temporal_metadata(text):
    normalized = (text or "").lower()

    due_date = None
    signals = []

    if "tomorrow" in normalized:
        due_date = datetime.now().date() + timedelta(days=1)
        signals.append("tomorrow")

    elif "today" in normalized or "tonight" in normalized:
        due_date = datetime.now().date()
        signals.append("today")

    cleaned_title = cleanup_temporal_tokens(text)

    metadata = {
        "raw_text": text,
        "cleaned_title": cleaned_title,
        "due_date": due_date,
        "signals": signals,
    }

    print("[Temporal Authority]", metadata)

    return metadata

__all__ = [
    "extract_temporal_metadata",
    "cleanup_temporal_tokens",
    "strip_temporal_language",
]