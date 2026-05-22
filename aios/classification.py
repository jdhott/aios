import re

from aios.text_utils import words_in


COMMON_ACTION_VERBS = [
    # Communication / admin
    "get", "call", "email", "message", "text", "reply", "follow", "schedule",
    "book", "confirm", "cancel", "reschedule",

    # Work / general tasks
    "update", "change", "review", "check", "submit", "send", "write",
    "read", "edit", "prepare", "plan", "organize", "create",
    "design", "redesign", "draft", "develop", "mockup",
    "build", "launch", "arrange", "set", "setup", "configure", "make", "complete", "bulk",

    # Digital / systems
    "upload", "download", "install", "run", "test", "fix",
    "replace", "add", "remove", "sort", "file", "print", "backup",

    # Login / access
    "log", "login", "sign", "signin", "sign-in",

    # Errands / life admin
    "buy", "order", "pick", "pickup", "drop", "dropoff",
    "deliver", "return", "renew", "pay", "deposit",

    # Household / physical tasks
    "pack", "unpack", "package", "label", "wrap",
    "bring", "take", "carry",
    "wash", "clean", "tidy", "wipe", "scrub", "rinse",
    "sweep", "vacuum", "mop",
    "fold", "hang", "put", "store", "tidy",
    "empty", "fill", "load", "unload",

    # Kitchen / bakery
    "cook", "bake", "prep", "mix", "shape",
    "feed", "refresh", "scale", "weigh", "mill",
    "slice", "cut", "pack", "label", "deliver",

    # Misc useful verbs
    "find", "look", "track", "measure", "record",
    "clarify",
]


QUICK_WIN_ACTION_VERBS = {
    # Communication / admin
    "get", "call", "email", "message", "text", "reply", "follow", "confirm",

    # Scheduling / coordination
    "book", "schedule", "reschedule", "cancel",

    # Transactions / errands
    "get", "pay", "buy", "order", "return", "renew", "deposit",

    # Quick digital actions
    "update", "check", "submit", "send", "print", "file", "upload", "download",

    # Pickup / movement
    "pick", "pickup", "drop", "dropoff", "bring", "take",

    # Household / light physical tasks
    "pack", "unpack", "label", "wrap", "wash", "clean", "wipe", "sort", "store",

    # Simple utility actions
    "find", "look", "replace", "add", "remove", "fix", "test", "run",
}


NOT_QUICK_WIN_WORDS = {
    "plan",
    "research",
    "prepare",
    "design",
    "develop",
    "figure out",
    "organize",
    "investigate",
    "explore",
    "review",
}


VAGUE_WORDS = [
    "thing",
    "stuff",
    "guy",
    "someone",
    "something",
]


WEAK_REFERENCE_WORDS = [
    "this",
    "that",
    "it",
]


OBVIOUS_SINGLE_STEP_TASKS = {
    "shower",
    "brush teeth",
    "floss",
    "wash face",
    "wash hands",
    "get dressed",
    "go to bed",
    "wake up",
    "take vitamins",
    "take medication",
    "eat breakfast",
    "eat lunch",
    "eat dinner",
}


ATOMIC_ACTION_VERBS = [
    "get",
    "open",
    "reopen",
    "restart",
    "call",
    "email",
    "text",
    "check",
    "review",
    "change",
    "replace",
    "print",
    "buy",
    "order",
    "book",
    "pay",
    "submit",
    "schedule",
    "cancel",
    "renew",
    "pair",
    "connect",
]


SAFE_NOUN_TASK_ACTIONS = [
    (r"\b(grocery|shopping|packing|to[- ]do)\s+list\b", "Create"),
    (r"\bmeal\s+plan\b", "Create"),
    (r"\b(packaging\s+)?labels?\b", "Create"),
    (r"\bstickers?\b", "Create"),
    (r"\b(canva\s+)?draft\b", "Create"),
    (r"\bprinter\s+drivers?\b", "Install"),
    (r"\bearbuds?\b", "Set up"),
    (r"\b(tax\s+)?documents?\b", "Review"),
    (r"\bforms?\b", "Review"),
    (r"\bschool\s+bread\s+order\b", "Prepare"),
    (r"\bbread\s+order\b", "Prepare"),
]


def contains_vague_word(title):
    words = words_in(title)
    return any(word in VAGUE_WORDS for word in words)


def contains_weak_reference(title):
    words = words_in(title)
    return any(word in WEAK_REFERENCE_WORDS for word in words)


def starts_with_action_verb(title):
    words = words_in(title)
    return bool(words) and words[0] in COMMON_ACTION_VERBS


def has_action_verb(title):
    words = words_in(title)
    return any(word in COMMON_ACTION_VERBS for word in words)


def title_starts_with_quick_win_verb(title):
    """Return True when a title starts with a known quick-win action verb."""
    if not title:
        return False

    words = words_in(title)
    if not words:
        return False

    return words[0] in QUICK_WIN_ACTION_VERBS


def is_obvious_single_step_task(title):
    """Return True for obvious routines that should not trigger clarification."""
    text = re.sub(r"\s+", " ", str(title or "").lower()).strip()

    if not text or text.startswith("clarify next action:"):
        return False

    return text in OBVIOUS_SINGLE_STEP_TASKS


def is_atomic_action(title):
    """Return True for clear, single-execution tasks that should not clarify."""
    text = title.lower().strip()
    words = words_in(title)

    if not words or text.startswith("clarify next action:"):
        return False

    first_word = words[0]

    if first_word not in ATOMIC_ACTION_VERBS:
        return False

    if contains_vague_word(title):
        return False

    return len(words) >= 2


def is_creative_task(title):
    """Return True for clear creative/design work that should not be clarified."""
    text = title.lower().strip()
    words = words_in(title)

    if not text or text.startswith("clarify next action:"):
        return False

    if contains_vague_word(title) or contains_weak_reference(title):
        return False

    creative_verbs = [
        "design",
        "redesign",
        "create",
        "draft",
        "develop",
        "mockup",
        "mock",
        "write",
        "edit",
        "revise",
    ]

    creative_objects = [
        "label",
        "labels",
        "logo",
        "brand",
        "branding",
        "canva",
        "caption",
        "post",
        "copy",
        "description",
        "announcement",
        "menu",
        "flyer",
        "poster",
        "layout",
        "mockup",
        "graphic",
        "document",
        "guide",
        "handout",
        "page",
        "website",
    ]

    starts_with_creative_verb = bool(words) and words[0] in creative_verbs
    mentions_creative_object = any(obj in text for obj in creative_objects)

    return starts_with_creative_verb and mentions_creative_object


def is_process_task(title):
    """Return True for clear process/project tasks."""
    text = title.lower().strip()

    if not text or text.startswith("clarify next action:"):
        return False

    if is_atomic_action(title):
        return False

    if contains_vague_word(title) or contains_weak_reference(title):
        return False

    process_keywords = [
        "setup",
        "set up",
        "install",
        "configure",
        "prepare",
        "plan",
        "organize",
        "build",
        "launch",
    ]

    if any(keyword in text for keyword in process_keywords):
        return True

    if is_creative_task(title):
        return True

    return False


def preferred_action_for_noun_task(title):
    """Return a safe deterministic verb for common noun-only task titles."""
    text = title.lower().strip()

    if not text or starts_with_action_verb(title):
        return None

    if contains_vague_word(title) or contains_weak_reference(title):
        return None

    for pattern, action in SAFE_NOUN_TASK_ACTIONS:
        if re.search(pattern, text):
            return action

    return None


def rewrite_safe_noun_task(title):
    """Deterministically add an action verb to safe noun-only tasks."""
    action = preferred_action_for_noun_task(title)

    if not action:
        return title

    words = words_in(title)
    if words and words[0].lower() == action.lower():
        return title

    return f"{action} {title[0].lower()}{title[1:]}"


def needs_action_verb(title):
    """Return True when a title has no leading action verb and needs intervention."""
    words = words_in(title)

    if not words:
        return True

    if starts_with_action_verb(title):
        return False

    if is_atomic_action(title) or is_process_task(title) or is_obvious_single_step_task(title):
        return False

    return True


def is_bare_noun_phrase(title):
    words = words_in(title)

    if not words:
        return True

    if is_atomic_action(title) or is_process_task(title):
        return False

    if starts_with_action_verb(title):
        return False

    return True


def needs_ai_cleanup(title):
    if is_atomic_action(title) or is_process_task(title) or is_obvious_single_step_task(title):
        return False

    return (
        contains_vague_word(title)
        or contains_weak_reference(title)
        or is_bare_noun_phrase(title)
    )


def is_still_vague(title):
    lower = title.lower().strip()

    if is_atomic_action(title) or is_process_task(title) or is_obvious_single_step_task(title):
        return False

    if lower.startswith("clarify next action:"):
        return True

    if contains_vague_word(title):
        return True

    if contains_weak_reference(title) and not starts_with_action_verb(title):
        return True

    if is_bare_noun_phrase(title) and not starts_with_action_verb(title):
        return True

    return False


def needs_soft_rewrite(title):
    words = words_in(title)

    if needs_ai_cleanup(title):
        return False

    if len(words) <= 3 and title_starts_with_quick_win_verb(title):
        return False

    return (
        starts_with_action_verb(title)
        and len(words) <= 5
        and not contains_vague_word(title)
        and not contains_weak_reference(title)
        and not is_bare_noun_phrase(title)
    )


def is_structurally_vague(title):
    words = words_in(title)
    vague_count = sum(1 for word in words if word in VAGUE_WORDS)

    return (
        vague_count > 0
        and len(words) <= 5
    )
