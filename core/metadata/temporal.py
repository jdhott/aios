from __future__ import annotations
import re
from datetime import datetime, timedelta

TEMPORAL_REGEX = re.compile(
    r"\btomorrow morning\b|\btomorrow afternoon\b|\btomorrow evening\b|\bthis morning\b|\bthis afternoon\b|\bthis evening\b|\btoday\b|\btonight\b|\btomorrow\b",
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

    return {
        "raw_text": text,
        "cleaned_title": cleanup_temporal_tokens(text),
        "due_date": due_date,
        "signals": signals,
    }

__all__ = [
    "extract_temporal_metadata",
    "cleanup_temporal_tokens",
    "strip_temporal_language",
]
