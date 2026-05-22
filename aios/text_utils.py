import re

MATCH_WORD_EQUIVALENTS = {
    "book": "schedule",
    "schedule": "schedule",
    "reserve": "schedule",
    "arrange": "schedule",
    "call": "contact",
    "email": "contact",
    "message": "contact",
    "text": "contact",
    "visit": "appointment",
    "appt": "appointment",
    "appointment": "appointment",
    "support": "service",
    "help": "service",
}

DUE_DATE_WORD_PATTERNS = [
    r"\b(?:by|due|on|for)\s+(?:today|tomorrow)\s+(?:morning|afternoon|evening|night)\b",
    r"\b(?:by|due|on|for)\s+(?:today|tomorrow|tonight)\b",
    r"\b(?:by|due|on|for)\s+this\s+(?:morning|afternoon|evening|week|weekend)\b",
    r"\b(?:by|due|on|for)\s+next\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|week|weekend)\b",
    r"\b(?:by|due|on|for)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    r"\b(?:today|tomorrow)\s+(?:morning|afternoon|evening|night)\b",
    r"\btoday\b",
    r"\btomorrow\b",
    r"\btonight\b",
    r"\bthis\s+(?:morning|afternoon|evening|week|weekend)\b",
    r"\bnext\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|week|weekend)\b",
]


def words_in(title):
    return re.findall(r"\b\w+\b", title.lower())


def normalize(text):
    text = re.sub(r"\s+", " ", text.strip().lower())
    words = text.split()
    normalized_words = [
        MATCH_WORD_EQUIVALENTS.get(word, word)
        for word in words
    ]
    return " ".join(normalized_words)


def clean_task_title(text):
    title = text.strip()

    title = re.sub(
        r"^(remember to|need to|i need to|todo:|to do:)\s+",
        "",
        title,
        flags=re.IGNORECASE,
    )

    title = re.sub(r"\s+", " ", title).strip()

    if title:
        title = title[0].upper() + title[1:]

    return title



def strip_due_date_phrases(text):
    t = str(text or "").strip()

    changed = True

    while changed:
        previous = t

        for pattern in DUE_DATE_WORD_PATTERNS:
            leading_pattern = rf"^\s*(?:{pattern})(?=\s|$|[,\.;:!?-])\s*"
            trailing_pattern = rf"(?:^|\s)(?:{pattern})\s*$"

            t = re.sub(leading_pattern, "", t, flags=re.IGNORECASE).strip()
            t = re.sub(trailing_pattern, "", t, flags=re.IGNORECASE).strip()

        t = re.sub(r"\s+", " ", t).strip()
        t = re.sub(r"\s+([,.;:!?])", r"\1", t)
        t = re.sub(r"([,.;:!?])\s*$", "", t).strip()
        t = re.sub(r"^[\-\–\—\:\|\(\)\[\]\s]+", "", t).strip()
        t = re.sub(r"[\-\–\—\:\|\(\)\[\]\s]+$", "", t).strip()

        changed = t != previous

    return t

def restore_preferred_proper_nouns(text):
    if not text:
        return text


STOPWORDS_FOR_ENTITY_EXTRACTION = {
    "the", "a", "an", "for", "to", "of", "and", "with",
    "on", "in", "today", "tomorrow", "important", "urgent", "asap",
}

GENERIC_OPERATIONAL_WORDS = {
    "measure", "mill", "prep", "prepare", "bake", "mix", "shape",
    "package", "clean", "check", "confirm", "schedule", "review",
    "update", "buy", "flour", "bread", "dough", "task", "project",
}

ENTITY_PATTERNS = [
    r"\bfor\s+(.+)$",
    r"\babout\s+(.+)$",
    r"\bregarding\s+(.+)$",
]


def extract_primary_operational_entity(text):
    if not text:
        return ""

    lowered = normalize(text)

    for pattern in ENTITY_PATTERNS:
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if match:
            entity = match.group(1).strip()
            entity = re.sub(r"[^a-z0-9\s]", " ", entity)
            entity = re.sub(r"\s+", " ", entity).strip()
            return entity

    tokens = words_in(lowered)

    filtered = [
        token
        for token in tokens
        if token not in STOPWORDS_FOR_ENTITY_EXTRACTION
        and token not in GENERIC_OPERATIONAL_WORDS
    ]

    return " ".join(filtered).strip()


def entity_similarity(entity_a, entity_b):
    if not entity_a or not entity_b:
        return 0.0

    return SequenceMatcher(None, entity_a, entity_b).ratio()


def apply_entity_divergence_penalty(base_score, task_a, task_b, diagnostics=False):
    entity_a = extract_primary_operational_entity(task_a)
    entity_b = extract_primary_operational_entity(task_b)

    similarity = entity_similarity(entity_a, entity_b)

    adjusted_score = base_score

    if entity_a and entity_b:
        if similarity < 0.35:
            adjusted_score *= 0.15
        elif similarity < 0.55:
            adjusted_score *= 0.50

    if diagnostics:
        return {
            "base_score": round(base_score, 3),
            "adjusted_score": round(adjusted_score, 3),
            "entity_a": entity_a,
            "entity_b": entity_b,
            "entity_similarity": round(similarity, 3),
        }

    return adjusted_score

    replacements = {
        r"\bmum\b": "Mum",
        r"\bmum's\b": "Mum's",
        r"\bdad\b": "Dad",
        r"\bdad's\b": "Dad's",
    }

    fixed = text
    for pattern, replacement in replacements.items():
        fixed = re.sub(pattern, replacement, fixed, flags=re.IGNORECASE)

    return fixed
