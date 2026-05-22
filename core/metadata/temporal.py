from __future__ import annotations

import re
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# Canonical Temporal Authority
# -----------------------------------------------------------------------------

TEMPORAL_PATTERNS = [
    r"\btoday\b",
    r"\btonight\b",
    r"\btomorrow\b",
    r"\btomorrow morning\b",
    r"\btomorrow afternoon\b",
    r"\btomorrow evening\b",
    r"\bthis morning\b",
    r"\bthis afternoon\b",
    r"\bthis evening\b",
]

MONTH_NAMES = (
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december"
)

TEMPORAL_DATE_REGEX = re.compile(
    r"\b(?:"
    + "|".join(MONTH_NAMES)
    + r")\s+\d{1,2}(?:st|nd|rd|th)?\b",
    re.IGNORECASE,
)

TEMPORAL_SIGNAL_REGEX = re.compile(
    "|".join(TEMPORAL_PATTERNS),
    re.IGNORECASE,
)

TEMPORAL_NORMALIZATION_MAP = {
    "today": "today",
    "tonight": "today",
    "this morning": "today",
    "this afternoon": "today",
    "this evening": "today",
    "tomorrow": "tomorrow",
    "tomorrow morning": "tomorrow",
    "tomorrow afternoon": "tomorrow",
    "tomorrow evening": "tomorrow",
}

def detect_temporal_signals(text):
    if not text:
        return []

    matches = []

    for match in TEMPORAL_SIGNAL_REGEX.finditer(text):
        matches.append(match.group(0).strip().lower())

    for match in TEMPORAL_DATE_REGEX.finditer(text):
        matches.append(match.group(0).strip())

    return list(dict.fromkeys(matches))

def normalize_temporal_signal(signal):
    if not signal:
        return None

    lowered = signal.strip().lower()

    if lowered in TEMPORAL_NORMALIZATION_MAP:
        return TEMPORAL_NORMALIZATION_MAP[lowered]

    return lowered

def canonical_due_date_from_signal(signal, today=None):
    if not signal:
        return None

    today = today or datetime.now().date()

    normalized = normalize_temporal_signal(signal)

    if normalized == "today":
        return today

    if normalized == "tomorrow":
        return today + timedelta(days=1)

    try:
        parsed = datetime.strptime(normalized, "%B %d")
        return parsed.replace(year=today.year).date()

    except Exception:
        return None

def strip_temporal_language(text):
    if not text:
        return text

    cleaned = TEMPORAL_SIGNAL_REGEX.sub("", text)
    cleaned = TEMPORAL_DATE_REGEX.sub("", cleaned)

    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\s+-\s+", " - ", cleaned)

    return cleaned.strip(" -")

def extract_temporal_metadata(text):
    signals = detect_temporal_signals(text)

    canonical_signals = [
        normalize_temporal_signal(signal)
        for signal in signals
    ]

    due_date = None

    for signal in canonical_signals:
        due_date = canonical_due_date_from_signal(signal)

        if due_date:
            break

    cleaned_title = strip_temporal_language(text)

    metadata = {
        "raw_text": text,
        "signals": canonical_signals,
        "due_date": due_date,
        "cleaned_title": cleaned_title,
    }

    print("[Temporal Authority]", metadata)

    return metadata