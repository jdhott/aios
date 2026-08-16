# Project candidate and write-back helpers extracted from run_aios.py.
#
# This module is intentionally dependency-injected from run_aios.py for this
# first modularization pass. That keeps behaviour stable while reducing the
# size of the orchestration script.

import os
import re
import requests
from datetime import datetime, timezone

from aios import operational_neighbor_reinforcement as onr


def configure_project_module(context):
    """Inject run_aios globals used by project helpers.

    This is a transitional seam: once more modules are extracted, these
    dependencies can become explicit function arguments or a small context object.
    """
    globals().update(context)


# Safe defaults so importing this module never runs live work by itself.
# run_aios.py calls configure_project_module(globals()) after import, so these
# values are replaced at runtime. Defaults must still exist because this module
# builds a few normalized constants during import.
TEST_MODE = False
DRY_RUN = True
RUN_PROJECT_CANDIDATE_DETECTOR = False
RUN_PROJECT_RELATION_WRITEBACK = False
RUN_PROJECT_STUB_CREATION = False
PROJECT_RELATION_WRITEBACK_RAW = None
PROJECT_CANDIDATE_MIN_RELATED_TASKS = 1
RUN_EXISTING_TASK_PROJECT_DISCOVERY = os.getenv("RUN_EXISTING_TASK_PROJECT_DISCOVERY", "true").strip().lower() in {"1", "true", "yes", "on"}
PROJECT_DISCOVERY_SCAN_LIMIT = int(os.getenv("PROJECT_DISCOVERY_SCAN_LIMIT", "100"))
PROJECT_REVIEW_LINK_STUBS = os.getenv("PROJECT_REVIEW_LINK_STUBS", "true").strip().lower() in {"1", "true", "yes", "on"}
PROJECT_DISCOVERY_MIN_CONFIDENCE = float(os.getenv("PROJECT_DISCOVERY_MIN_CONFIDENCE", "0.70"))
PROJECT_DISCOVERY_MAX_REVIEW_PROJECTS = int(os.getenv("PROJECT_DISCOVERY_MAX_REVIEW_PROJECTS", "5"))
PROJECT_DISCOVERY_MAX_NEW_PER_RUN = int(os.getenv("PROJECT_DISCOVERY_MAX_NEW_PER_RUN", "5"))
PROJECT_INCREMENTAL_AFFINITY_MIN_CONFIDENCE = float(os.getenv("PROJECT_INCREMENTAL_AFFINITY_MIN_CONFIDENCE", "0.82"))
PROJECT_CLUSTER_REVIEW_MIN_CONFIDENCE = float(os.getenv("PROJECT_CLUSTER_REVIEW_MIN_CONFIDENCE", "0.75"))
RUN_PROJECT_INCREMENTAL_AFFINITY = os.getenv("RUN_PROJECT_INCREMENTAL_AFFINITY", "true").strip().lower() in {"1", "true", "yes", "on"}

# ============================================================
# B2 RUNTIME PERFORMANCE FLAGS
# ============================================================

ENABLE_B2_DIAGNOSTICS = False


def b2_log(message):
    """Lightweight gated diagnostics logger for B2 ontology cognition."""
    if ENABLE_B2_DIAGNOSTICS:
        print(message)


PROJECTS_DATABASE_ID = (
    os.getenv("PROJECTS_DATABASE_ID")
    or os.getenv("PROJECT_DATABASE_ID")
    or os.getenv("NOTION_PROJECTS_DATABASE_ID")
    or os.getenv("NOTION_PROJECT_DATABASE_ID")
    or ""
)
SUGGESTED_PROJECT_PROPERTY = os.getenv("SUGGESTED_PROJECT_PROPERTY", "Suggested Project")
TASK_PROJECT_RELATION_PROPERTY = os.getenv("TASK_PROJECT_RELATION_PROPERTY", "Project")
PROJECT_TITLE_PROPERTY = os.getenv("PROJECT_TITLE_PROPERTY", "Project Name")
PROJECT_STATUS_PROPERTY = os.getenv("PROJECT_STATUS_PROPERTY", "Status")
PROJECT_ACTIVE_PROPERTY = os.getenv("PROJECT_ACTIVE_PROPERTY", "Active")
PROJECT_STUB_STATUS_VALUE = os.getenv("PROJECT_STUB_STATUS_VALUE", "Someday")
PROJECT_LINK_MIN_CONFIDENCE = float(os.getenv("PROJECT_LINK_MIN_CONFIDENCE", "0.85"))
PROJECT_LINK_MIN_MATCH_SCORE = float(os.getenv("PROJECT_LINK_MIN_MATCH_SCORE", "0.92"))


# ============================================================
# DOMAIN-AWARE PROJECT SIMILARITY
# ============================================================

DOMAIN_ANCHOR_WORDS = {
    "pool",
    "bakery",
    "bread",
    "office",
    "garden",
    "tax",
    "aios",
    "workshop",
}

GENERIC_OPERATIONAL_WORDS = {
    "management",
    "operations",
    "maintenance",
    "workflow",
    "coordination",
    "supplies",
    "equipment",
    "organization",
}




# ============================================================
# CANONICAL SIMPLICITY BIAS
# ============================================================

CANONICAL_SIMPLICITY_PENALTY_WORDS = {
    "equipment",
    "supplies",
    "management",
    "coordination",
    "organization",
    "tracking",
    "workflow",
}


def canonical_simplicity_bonus(project_name):

    tokens = re.findall(
        r"[a-zA-Z]+",
        str(project_name or "").lower(),
    )

    penalty = 0.0

    for token in tokens:

        if token in CANONICAL_SIMPLICITY_PENALTY_WORDS:
            penalty += 0.08

    # Prefer shorter broad operational domains
    if len(tokens) <= 4:
        penalty -= 0.05

    return max(0.0, penalty)


def weighted_project_tokens(text):
    tokens = re.findall(r"[a-zA-Z]+", str(text or "").lower())

    weighted = []

    for token in tokens:

        if token in DOMAIN_ANCHOR_WORDS:
            weighted.extend([token] * 5)

        elif token in GENERIC_OPERATIONAL_WORDS:
            weighted.append(token)

        else:
            weighted.extend([token] * 2)

    return weighted


def weighted_similarity(a, b):

    a_tokens = set(weighted_project_tokens(a))
    b_tokens = set(weighted_project_tokens(b))

    if not a_tokens or not b_tokens:
        return 0.0

    overlap = len(a_tokens & b_tokens)
    union = len(a_tokens | b_tokens)

    score = overlap / union

    # Strong boost for shared operational anchor
    shared_anchors = (
        a_tokens & b_tokens & DOMAIN_ANCHOR_WORDS
    )

    if shared_anchors:
        score += 0.20

    return min(score, 1.0)


PROJECT_LINK_AMBIGUITY_MARGIN = float(os.getenv("PROJECT_LINK_AMBIGUITY_MARGIN", "0.08"))
ACTIVE_PROJECT_STATUS_VALUES = {"Active", "In Progress", "Current", "Ongoing"}
INACTIVE_PROJECT_STATUS_VALUES = {"Completed", "Done", "Archived", "Paused", "Someday"}
# ## 13.2 Project candidate detector

PROJECT_TOKEN_STOPWORDS = {
    "the", "and", "for", "with", "from", "into", "onto", "about", "this",
    "that", "task", "tasks", "project", "next", "new", "first", "current",
    "today", "tomorrow", "week", "weekend", "morning", "afternoon", "evening",
    "call", "email", "text", "message", "ask", "reply", "follow", "check",
    "review", "update", "create", "draft", "design", "prepare", "plan",
    "organize", "research", "setup", "install", "fix", "open", "buy", "order",
    "make", "do", "get", "set", "add", "remove", "print", "send",
    # Project detector: family alone is too broad; require concrete room/cleanup/coordination signals.
    "family", "members",
}

# Project candidate tuning ----------------------------------------------------
# The detector should group tasks around outcomes / operational domains, not
# around incidental bakery nouns. These token groups intentionally affect only
# project-candidate review. They do not affect task creation, breakdowns,
# duplicate detection or Quick Win.

PROJECT_LOW_VALUE_DOMAIN_TOKENS = {
    # Generic bakery / formula vocabulary. Useful in task titles, but weak as a
    # project signal because otherwise every bread task clusters together.
    "bakery", "bake", "baking", "bread", "breads", "loaf", "loaves",
    "sourdough", "starter", "levain", "dough", "flour", "grain", "grains",
    "wheat", "rye", "khorasan", "fife", "red", "seed", "seeds", "seeded",
    "inclusion", "inclusions", "soaker", "porridge", "recipe", "recipes",
    "sheet", "sheets", "formula", "mix", "bulk", "shape", "proof", "bake",
    "tin", "artisan", "focaccia", "baguette", "cranberry", "walnut",
    "multi", "multiseed", "buttermilk", "cinnamon", "raisin",
}

PROJECT_HIGH_VALUE_TOKENS = {
    # External stakeholders / durable operational domains.
    "school", "workshop", "workshops", "class", "classes", "teaching",
    "student", "students", "customer", "customers", "supplier", "supplies",
    "costco", "stickers", "labels", "packaging", "inventory", "stock",
    "equipment", "lame", "cover", "orders", "pickup", "delivery",
    "tax", "income", "refund", "bank", "excel",
    "room", "living", "garbage", "recycling", "kleenex", "blanket",
    "dishes", "dish", "pool", "tools", "maintenance",
}

PROJECT_CATEGORY_RULES = {
    "School Bread Program": {
        "school", "breakfast", "program",
    },
    "Weekly Bakery Production": {
        "starter", "levain", "soaker", "mise", "ingredients", "production",
        "rotation", "mix", "bulk", "shape", "bake", "prep", "dough",
    },
    "Bakery Operations and Supplies": {
        "supplies", "supplier", "suppliers", "stickers", "labels", "packaging", "inventory",
        "stock", "equipment", "lame", "cover", "bags", "bag", "organize", "organise",
    },
    "Recipe and Documentation Management": {
        "recipe", "recipes", "transcribe", "post", "send",
        "documentation", "document", "guide", "mary",
    },
    "Workshops and Teaching": {
        "workshop", "workshops", "class", "classes", "teaching", "student",
        "students", "dates", "summary", "summaries", "samples", "gaby",
    },
    "Tax Preparation": {
        "tax", "taxes", "accountant", "cra", "return", "returns",
        "receipt", "receipts", "refund", "excel",
    },
    "Household Cleanup and Maintenance": {
        # Do not include bare "family" here. "Family calendar" and family-care
        # coordination are not cleanup/maintenance projects. Concrete room/chore
        # tokens still allow real household-maintenance clusters.
        "room", "living", "garbage", "recycling", "kleenex", "blanket",
        "household", "cleanup", "cleaning", "wash", "replace",
        "dishes", "dish", "pool", "tools", "maintenance",
    },
}


def project_category_labels(title):
    """Return operational project categories suggested by a task title."""
    tokens = set(words_in(title))
    labels = []

    for label, signals in PROJECT_CATEGORY_RULES.items():
        if tokens & signals:
            labels.append(label)

    return labels


def project_category_overlap(title_a, title_b):
    """Return shared high-level category labels for two task titles."""
    labels_a = set(project_category_labels(title_a))
    labels_b = set(project_category_labels(title_b))
    return labels_a & labels_b


PROJECT_COORDINATION_TOKENS = {
    "calendar", "calendars", "schedule", "scheduling", "trip", "travel",
    "appointment", "appointments", "doctor", "dr", "clinic", "take", "drive",
}

PROJECT_CLEANUP_MAINTENANCE_TOKENS = {
    "room", "living", "garbage", "recycling", "kleenex", "blanket",
    "household", "cleanup", "cleaning", "clean", "wash", "dishes",
    "dish", "pool", "tools", "maintenance", "repair", "replace",
}


PROJECT_PERSONAL_FOOD_TOKENS = {
    "chicken", "beef", "pork", "fish", "meat", "turkey", "groceries",
    "grocery", "fridge", "freezer", "freeze", "frozen", "meal", "meals",
    "dinner", "lunch", "breakfast", "leftovers",
}

PROJECT_TAX_CORE_TOKENS = {
    "tax", "taxes", "accountant", "cra", "return", "returns",
    "receipt", "receipts", "refund", "t4", "t5", "rrsp", "excel",
}

PROJECT_BAKERY_OPS_CORE_TOKENS = {
    "bakery", "bread", "breads", "orders", "customer", "customers",
    "supplies", "supplier", "suppliers", "stickers", "labels", "packaging",
    "inventory", "stock", "equipment", "lame", "cover", "bags", "bag",
}

PROJECT_WEAK_CONTEXT_TOKENS = {
    "bank", "money", "cash", "costco", "store", "stores", "shop", "shopping",
}

PROJECT_HOUSEHOLD_LOCATION_TOKENS = {
    "basement", "garage", "upstairs", "downstairs", "closet",
    "shed", "pantry", "laundry", "attic",
}

PROJECT_RETRIEVAL_ACTION_TOKENS = {
    "get", "grab", "bring", "take", "fetch", "move", "carry",
}


def is_household_retrieval_task(title):
    """Return True for lightweight household retrieval/support actions."""
    tokens = set(words_in(title))

    has_location = bool(tokens & PROJECT_HOUSEHOLD_LOCATION_TOKENS)
    has_retrieval_action = bool(tokens & PROJECT_RETRIEVAL_ACTION_TOKENS)

    # Require strong bakery-operations language before allowing project links.
    has_strong_bakery_ops = bool(tokens & {
        "inventory", "packaging", "supplier", "supplies", "equipment",
        "production", "orders", "labels",
    })

    return has_location and has_retrieval_action and not has_strong_bakery_ops


def project_task_domains(title):
    """Return coarse domains used only as a project-candidate drift guard.

    This prevents broad life-context words from bridging unrelated work. For
    example, family calendar / appointments / trips are coordination domains,
    while dishes / recycling / pool tools are cleanup-maintenance domains.
    """
    text = re.sub(r"\s+", " ", str(title or "").lower()).strip()
    tokens = set(words_in(text))
    domains = set()

    if tokens & PROJECT_CLEANUP_MAINTENANCE_TOKENS:
        domains.add("household_cleanup_maintenance")

    if tokens & PROJECT_COORDINATION_TOKENS:
        domains.add("family_scheduling_coordination")

    # "family room" is a physical place; bare "family" is only context.
    if "family room" in text:
        domains.add("household_cleanup_maintenance")

    # Family + scheduling/care/travel wording is coordination, not cleanup.
    if "family" in tokens and (tokens & PROJECT_COORDINATION_TOKENS):
        domains.add("family_scheduling_coordination")

    return domains


def project_candidate_has_domain_drift(seed_title, result):
    """Return True when a proposed group crosses unrelated life domains."""
    titles = [seed_title] + (result.get("related_titles", []) or [])
    domains_by_title = [project_task_domains(title) for title in titles]
    all_domains = set().union(*domains_by_title) if domains_by_title else set()

    # A household cleanup project must not absorb family calendar, travel, or
    # appointment coordination merely because all tasks occur in family life.
    if (
        result.get("project_name") == "Household Cleanup and Maintenance"
        and "family_scheduling_coordination" in all_domains
    ):
        return True

    return False


PROJECT_INSTITUTIONAL_CONTEXT_TOKENS = {
    "school", "breakfast", "program", "workshop", "workshops", "class",
    "classes", "student", "students", "supplier", "supplies",
    "inventory", "equipment", "tax", "taxes", "accountant", "cra",
}

PROJECT_NON_PERSON_RECIPIENT_WORDS = {
    "school", "program", "bakery", "costco", "notion", "aios", "chatgpt",
    "apple", "google", "siri", "supplier", "suppliers", "workshop",
    "class", "classes", "students", "student", "mum", "dad",
}


def project_personal_recipient_tokens(title):
    """Return person-name recipient tokens from phrases like 'for Tammy and Steve'.

    This is a project-candidate safety signal only. It prevents customer /
    household fulfilment tasks from being absorbed into institutional projects
    merely because they share generic words such as bread or order.
    """
    text = str(title or "")
    recipients = set()

    for match in re.finditer(
        r"\b(?:for|to)\s+([A-Z][a-z]+(?:\s+(?:and|&)\s+[A-Z][a-z]+){0,3})\b",
        text,
    ):
        phrase = match.group(1)
        names = re.findall(r"\b[A-Z][a-z]+\b", phrase)
        for name in names:
            token = name.lower()
            if token not in PROJECT_NON_PERSON_RECIPIENT_WORDS:
                recipients.add(token)

    return recipients


def project_has_institutional_context(title):
    """Return True when a title names an institutional / program context."""
    tokens = set(words_in(title))
    return bool(tokens & PROJECT_INSTITUTIONAL_CONTEXT_TOKENS)


def has_project_recipient_context_mismatch(title_a, title_b):
    """Return True for personal-recipient task vs institutional workflow mismatch."""
    personal_a = project_personal_recipient_tokens(title_a)
    personal_b = project_personal_recipient_tokens(title_b)
    institutional_a = project_has_institutional_context(title_a)
    institutional_b = project_has_institutional_context(title_b)

    return (personal_a and not institutional_a and institutional_b) or (
        personal_b and not institutional_b and institutional_a
    )


def project_meaningful_tokens(title):
    """Return stable title tokens for project-relatedness scoring.

    Generic bakery/formula tokens are intentionally removed here. This prevents
    noisy micro-projects such as Seed Bread Preparation, Sourdough Starter
    Maintenance, or Khorasan Bread Recipe Sharing from appearing merely because
    tasks share ingredient or loaf vocabulary.
    """
    tokens = []
    for token in words_in(title):
        if len(token) <= 2:
            continue
        if token in PROJECT_TOKEN_STOPWORDS:
            continue
        if token in PROJECT_LOW_VALUE_DOMAIN_TOKENS:
            continue
        tokens.append(token)
    return set(tokens)


def project_relation_score(title_a, title_b):
    """Score whether two task titles may belong to the same project.

    The score now favours shared operational outcomes/categories and devalues
    generic bakery vocabulary. It remains review-only: the AI layer still decides
    whether to log a project candidate.
    """
    if has_project_recipient_context_mismatch(title_a, title_b):
        return 0.0

    tokens_a = project_meaningful_tokens(title_a)
    tokens_b = project_meaningful_tokens(title_b)
    shared_categories = project_category_overlap(title_a, title_b)

    # Do not create candidates from generic bakery/formula overlap alone.
    if not tokens_a and not tokens_b and not shared_categories:
        return 0.0

    overlap = len(tokens_a & tokens_b)
    containment = overlap / max(min(len(tokens_a), len(tokens_b)), 1) if tokens_a and tokens_b else 0.0
    jaccard = overlap / max(len(tokens_a | tokens_b), 1) if tokens_a or tokens_b else 0.0
    sequence = SequenceMatcher(None, normalize(title_a), normalize(title_b)).ratio()

    category_score = 0.0
    if shared_categories:
        category_score = 0.70
        # Higher confidence when there is also a concrete shared token such as
        # school, workshop, tax, family room, Costco, stickers, etc.
        if overlap > 0:
            category_score = 0.85

    # Shared high-value tokens are better than generic lexical overlap.
    high_value_overlap = len((set(words_in(title_a)) & set(words_in(title_b))) & PROJECT_HIGH_VALUE_TOKENS)
    high_value_score = min(0.20 * high_value_overlap, 0.40)

    score = (
        0.45 * category_score
        + 0.25 * containment
        + 0.15 * jaccard
        + 0.10 * sequence
        + high_value_score
    )

    return round(min(score, 1.0), 3)


def is_project_candidate_source_task(task):
    """Return True for newly created tasks worth checking for project grouping."""
    if not task or task.get("dry_run"):
        return False

    title = get_title(task)
    if not title:
        return False

    # Explicit Brain Dump project intent must still be processed even if an
    # unrelated classifier routed the task to clarification. This guarantees
    # the review Project relation is created from authoritative user intent.
    if title.lower().startswith("clarify next action:") and not str(task.get("_manual_project_hint") or "").strip():
        return False

    # Subtasks already belong to a sequence under a parent task, so do not use
    # them as project-candidate seeds in V1.
    if get_parent_task_id(task):
        return False

    return True


def get_project_candidate_source_tasks():
    """Return top-level tasks created in this run that can seed review candidates."""
    return [
        task for task in globals().get("created_tasks", [])
        if is_project_candidate_source_task(task)
    ]



def get_recent_completed_tasks_for_operational_memory(limit=300):
    """Retrieve completed tasks as episodic reinforcement memory."""

    filter_payload = {
        "and": [
            {"property": "Done", "checkbox": {"equals": True}},
            {"property": "Archived", "checkbox": {"equals": False}},
        ]
    }

    try:
        tasks = query_tasks_database(
            filter_payload=filter_payload,
            sorts=[{"timestamp": "last_edited_time", "direction": "descending"}],
            page_size=limit,
        )

        print(
            "[Historical Operational Memory] "
            f"Loaded {len(tasks)} completed tasks"
        )

        for task in tasks:
            task["_episodic_memory_weight"] = 0.35

        return tasks

    except Exception as e:
        print(
            "[Historical Operational Memory Error] "
            f"{e}"
        )
        return []


def build_operational_context_task_set(open_tasks):
    """
    Combine active operational cognition with
    lower-weight episodic historical reinforcement.
    """

    open_tasks = list(open_tasks or [])

    for task in open_tasks:
        task["_episodic_memory_weight"] = 1.0

    completed_tasks = (
        get_recent_completed_tasks_for_operational_memory()
    )

    combined = open_tasks + completed_tasks

    print(
        "[Operational Context Layer] "
        f"open={len(open_tasks)} "
        f"historical={len(completed_tasks)} "
        f"combined={len(combined)}"
    )

    return combined


def get_open_tasks_for_project_candidate_scan():
    """Fetch open tasks for review-only project candidate detection."""
    filter_payload = {
        "and": [
            {"property": "Open Loop", "checkbox": {"equals": True}},
            {"property": "Done", "checkbox": {"equals": False}},
            {"property": "Archived", "checkbox": {"equals": False}},
        ]
    }

    return query_tasks_database(
        filter_payload=filter_payload,
        sorts=[{"timestamp": "created_time", "direction": "descending"}],
        page_size=globals().get('PROJECT_CANDIDATE_SCAN_LIMIT', 25),
    )



def task_has_project_relation(task):
    """Return True when a task already has any Project relation."""
    if not task:
        return False
    prop = (task.get("properties", {}) or {}).get(TASK_PROJECT_RELATION_PROPERTY, {})
    return bool(prop.get("relation") or [])


def get_existing_unprojected_tasks_for_discovery(open_tasks):
    """Return existing open tasks eligible for retroactive project emergence.

    This is intentionally review-oriented: tasks already assigned to a Project
    are excluded, as are clarification placeholders and child tasks.
    """
    eligible = []
    for task in open_tasks or []:
        if task_has_project_relation(task):
            continue
        if get_parent_task_id(task):
            continue
        title = get_title(task)
        if not title or title.lower().startswith("clarify next action:"):
            continue
        eligible.append(task)
    return eligible[:globals().get("PROJECT_DISCOVERY_SCAN_LIMIT", 50)]


def set_review_project_relation_if_empty(task, project, suggested_project):
    """Link a task to an inactive project stub strictly for manual review.

    The inactive Project row is the review object:
    - rename the project row to edit the proposed project name;
    - remove/add task relations to edit membership;
    - change project Status to Active to confirm the reviewed project.

    Existing Project relations are never overwritten.
    """
    if not globals().get("PROJECT_REVIEW_LINK_STUBS", True):
        return False
    if not task or not project or task.get("dry_run"):
        return False
    if is_active_project(project):
        return False
    if task_has_project_relation(task):
        return False
    if TEST_MODE or DRY_RUN:
        return False

    title = get_title(task)
    response = requests.patch(
        f"https://api.notion.com/v1/pages/{task['id']}",
        headers=headers,
        json={
            "properties": {
                TASK_PROJECT_RELATION_PROPERTY: {
                    "relation": [{"id": project["id"]}]
                }
            }
        },
        timeout=30,
    )
    if response.ok:
        increment_summary("project_relation_updates")
        print(f"Set REVIEW Project relation: {title} → {get_title(project)} (inactive; manual review required)")
        return True

    increment_summary("errors")
    print("ERROR setting review Project relation:", title)
    print(response.status_code, response.text)
    return False




# ============================================================
# OPERATIONAL DOMAIN EMERGENCE
# ============================================================

OPERATIONAL_DOMAIN_EMERGENCE_THRESHOLD = 0.45
OPERATIONAL_DOMAIN_MIN_REINFORCEMENT = 2


def should_emerge_new_operational_domain(
    seed_title,
    operational_inference,
    related_candidates,
):

    score = operational_inference.get(
        "score",
        0.0,
    )

    if score >= OPERATIONAL_DOMAIN_EMERGENCE_THRESHOLD:
        return False

    if len(related_candidates) < OPERATIONAL_DOMAIN_MIN_REINFORCEMENT:
        return False

    return True


def generate_emergent_operational_domain(
    seed_title,
    related_candidates,
):

    titles = [seed_title]

    for candidate in related_candidates[:5]:

        candidate_title = get_title(candidate)

        if candidate_title:
            titles.append(candidate_title)

    combined = " ".join(titles).lower()

    if any(
        word in combined
        for word in [
            "network",
            "internet",
            "router",
            "ethernet",
            "wifi",
            "wireless",
            "switch",
        ]
    ):
        return "Home Networking and Infrastructure"

    if any(
        word in combined
        for word in [
            "photo",
            "camera",
            "lens",
            "lighting",
        ]
    ):
        return "Photography and Media Workflow"

    return None














# ============================================================
# ONTOLOGY-AWARE EXPANSION
# ============================================================

def build_ontology_expansion_set(
    related_candidates,
    latent_cluster,
    operational_inference,
    open_tasks,
):

    expansion_titles = set()

    # Existing related candidates
    for task in related_candidates or []:

        title = get_title(task)

        if not title:
            continue

        reinforcement_weight = (
            calculate_operational_reinforcement_weight(
                title
            )
        )

        b2_log(
            "[Operational Reinforcement Weight] "
            f"{title} -> {reinforcement_weight:.2f}"
        )

        if reinforcement_weight < 0.30:

            b2_log(
                "[Ontology Hygiene Filter] "
                f"Suppressed weak operational neighbor: "
                f"{title}"
            )

            continue

        expansion_titles.add(title)

    # Latent operational memory
    for title in latent_cluster.get(
        "related_titles",
        []
    ):

        reinforcement_weight = (
            calculate_operational_reinforcement_weight(
                title
            )
        )

        if reinforcement_weight < 0.30:

            b2_log(
                "[Latent Ontology Hygiene Filter] "
                f"Suppressed latent neighbor: "
                f"{title}"
            )

            continue

        expansion_titles.add(title)

    # Operational reinforcement neighbor
    operational_project = operational_inference.get(
        "matched_project"
    )

    if operational_project:

        for task in open_tasks or []:

            task_title = get_title(task)

            if not task_title:
                continue

            props = task.get("properties", {}) if task else {}

            project_name = get_rich_text_plain_value(
                props,
                SUGGESTED_PROJECT_PROPERTY,
            )

            if not project_name:

                relation_ids = get_relation_ids(
                    props,
                    TASK_PROJECT_RELATION_PROPERTY,
                )

                if relation_ids:
                    project_name = "Linked Operational Project"

            if project_name == operational_project:
                expansion_titles.add(task_title)

    return sorted(expansion_titles)



# ============================================================
# ONTOLOGY CONFIDENCE OVERRIDE
# ============================================================

ONTOLOGY_CONFIDENCE_OVERRIDE_THRESHOLD = 0.55


def calculate_ontology_confidence(
    related_candidates,
    latent_cluster,
    exploratory_allowed,
    operational_inference,
):

    confidence = 0.0

    related_count = len(
        related_candidates or []
    )

    latent_count = len(
        latent_cluster.get(
            "related_titles",
            []
        )
    )

    operational_score = operational_inference.get(
        "score",
        0.0,
    )

    confidence += min(
        related_count * 0.05,
        0.30,
    )

    confidence += min(
        latent_count * 0.04,
        0.30,
    )

    if exploratory_allowed:
        confidence += 0.15

    if operational_score < 0.40:
        confidence += 0.15

    return round(
        min(confidence, 1.0),
        2,
    )


def should_override_legacy_validation(
    related_candidates,
    latent_cluster,
    exploratory_allowed,
    operational_inference,
):

    confidence = calculate_ontology_confidence(
        related_candidates,
        latent_cluster,
        exploratory_allowed,
        operational_inference,
    )

    return (
        confidence >= ONTOLOGY_CONFIDENCE_OVERRIDE_THRESHOLD,
        confidence,
    )





# ============================================================
# OPERATIONAL SPECIFICITY SCORING
# ============================================================

GENERIC_OPERATIONAL_WORDS = {
    "buy",
    "check",
    "move",
    "find",
    "wash",
    "read",
    "review",
    "garage",
    "backyard",
    "devices",
    "house",
    "home",
    "schedule",
}

INFRASTRUCTURE_SYSTEM_WORDS = {
    "router",
    "vlan",
    "network",
    "networking",
    "raspberry",
    "dashboard",
    "monitoring",
    "backup",
    "ups",
    "wifi",
    "configuration",
    "configure",
    "rack",
    "coverage",
    "infrastructure",
    "server",
    "iot",
    "system",
    "systems",
}


def calculate_operational_specificity(title):

    tokens = set(
        words_in(title)
    )

    infrastructure_score = len(
        tokens & INFRASTRUCTURE_SYSTEM_WORDS
    )

    generic_score = len(
        tokens & GENERIC_OPERATIONAL_WORDS
    )

    # ========================================================
    # STRUCTURAL OPERATIONAL SEMANTICS
    # ========================================================

    configuration_semantics = any([
        "configure" in tokens,
        "configuration" in tokens,
        "monitoring" in tokens,
        "dashboard" in tokens,
    ])

    infrastructure_topology = any([
        "network" in tokens,
        "networking" in tokens,
        "vlan" in tokens,
        "router" in tokens,
        "wifi" in tokens,
        "iot" in tokens,
    ])

    persistent_system_maintenance = any([
        "backup" in tokens,
        "ups" in tokens,
        "server" in tokens,
        "raspberry" in tokens,
        "rack" in tokens,
    ])

    semantic_bonus = 0

    if configuration_semantics:
        semantic_bonus += 2

    if infrastructure_topology:
        semantic_bonus += 2

    if persistent_system_maintenance:
        semantic_bonus += 2

    specificity = (
        infrastructure_score * 2
        + semantic_bonus
        - generic_score
    )

    return max(
        specificity,
        0,
    )


def calculate_operational_reinforcement_weight(
    title
):

    specificity = calculate_operational_specificity(
        title
    )

    if specificity >= 4:
        return 1.0

    if specificity >= 2:
        return 0.7

    if specificity >= 1:
        return 0.4

    return 0.1




# ============================================================
# B2 LIGHTWEIGHT RUNTIME CACHE
# ============================================================

_B2_RUNTIME_CACHE = {
    "normalized_tokens": {},
}


def get_cached_normalized_tokens(title):

    if not title:
        return set()

    cache = _B2_RUNTIME_CACHE["normalized_tokens"]

    if title in cache:
        return cache[title]

    normalized = set(
        onr.normalize_tokens(title)
    )

    cache[title] = normalized

    return normalized







# ============================================================
# B2 RELATIVE ATTRACTOR CONFIDENCE
# ============================================================

AMBIGUOUS_TOPOLOGY_MARGIN = 0.15


def calculate_relative_attractor_confidence(
    attractor_scores,
):

    if not attractor_scores:
        b2_log(
            f"[Exploratory Preservation] "
            f"{seed_title} retained as sparse topology"
        )

        return None

    ordered = sorted(
        attractor_scores,
        key=lambda x: x[1],
        reverse=True,
    )

    if len(ordered) == 1:
        return {
            "winner": ordered[0][0],
            "winner_score": ordered[0][1],
            "runner_up": None,
            "margin": 1.0,
            "ambiguous": False,
        }

    winner, winner_score = ordered[0]
    runner_up, runner_up_score = ordered[1]

    margin = winner_score - runner_up_score

    return {
        "winner": winner,
        "winner_score": winner_score,
        "runner_up": runner_up,
        "runner_up_score": runner_up_score,
        "margin": margin,
        "ambiguous": margin < AMBIGUOUS_TOPOLOGY_MARGIN,
    }


# ============================================================
# B2 FIELD STRENGTH LOCALITY DECAY
# ============================================================

def calculate_field_strength_locality_decay(
    seed_title,
    reinforcement_project,
    field_strength,
):

    normalized_seed = normalize_text(seed_title)

    infrastructure_hits = sum(
        1
        for keyword in INFRASTRUCTURE_KEYWORDS
        if keyword in normalized_seed
    )

    bakery_keywords = {
        "bread",
        "bakery",
        "flour",
        "oven",
        "dough",
        "starter",
        "grain",
        "milling",
        "focaccia",
        "sourdough",
        "packaging",
        "inventory",
        "order",
    }

    bakery_hits = sum(
        1
        for keyword in bakery_keywords
        if keyword in normalized_seed
    )

    locality_decay = 1.0

    # Infrastructure tasks should strongly resist bakery gravity
    if (
        infrastructure_hits >= 2
        and reinforcement_project == "Bakery Operations and Supplies"
        and bakery_hits == 0
    ):
        locality_decay *= 0.18

    # Infrastructure tasks should weaken generic household gravity
    if (
        infrastructure_hits >= 2
        and reinforcement_project
        in GENERIC_OPERATIONAL_DOMAINS
    ):
        locality_decay *= 0.55

    # Strong locality reinforcement for infrastructure domains
    if (
        infrastructure_hits >= 3
        and reinforcement_project
        in TECHNICAL_INFRASTRUCTURE_DOMAINS
    ):
        locality_decay *= 1.30

    return field_strength * locality_decay



# ============================================================
# B2 AMBIGUITY GOVERNANCE
# ============================================================

def should_flag_ambiguous_topology(
    relative_confidence,
):

    if not relative_confidence:
        return False

    return relative_confidence.get("ambiguous", False)


# ============================================================
# B2 REINFORCEMENT ADMISSION FILTERING
# ============================================================

TECHNICAL_INFRASTRUCTURE_DOMAINS = {
    "Home Networking and Infrastructure",
    "Home Network Backup and Maintenance",
    "Home Server and Monitoring",
}


def calculate_reinforcement_admission_score(
    seed_title,
    reinforcement_project,
):

    normalized_seed = normalize_text(seed_title)

    infrastructure_hits = sum(
        1
        for keyword in INFRASTRUCTURE_KEYWORDS
        if keyword in normalized_seed
    )

    bakery_keywords = {
        "bread",
        "bakery",
        "flour",
        "oven",
        "dough",
        "starter",
        "grain",
        "focaccia",
        "sourdough",
        "milling",
        "label",
        "packaging",
    }

    bakery_hits = sum(
        1
        for keyword in bakery_keywords
        if keyword in normalized_seed
    )

    admission_score = 1.0

    # Hard suppress bakery reinforcement for infrastructure tasks
    if (
        infrastructure_hits >= 2
        and reinforcement_project == "Bakery Operations and Supplies"
        and bakery_hits == 0
    ):
        admission_score *= 0.05

    # Strongly suppress generic household reinforcement
    if (
        infrastructure_hits >= 2
        and reinforcement_project
        in GENERIC_OPERATIONAL_DOMAINS
    ):
        admission_score *= 0.30

    # Infrastructure tasks should prefer infrastructure topology
    if infrastructure_hits >= 3:
        admission_score *= 1.25

    return admission_score


# ============================================================
# B2 LOCAL TOPOLOGY REINFORCEMENT
# ============================================================

def calculate_topology_locality_weight(
    seed_title,
    reinforcement_project,
):

    normalized_seed = normalize_text(seed_title)

    infrastructure_hits = sum(
        1
        for keyword in INFRASTRUCTURE_KEYWORDS
        if keyword in normalized_seed
    )

    bakery_keywords = {
        "bread",
        "bakery",
        "flour",
        "oven",
        "dough",
        "bake",
        "starter",
        "grain",
        "milling",
        "focaccia",
        "sourdough",
    }

    bakery_hits = sum(
        1
        for keyword in bakery_keywords
        if keyword in normalized_seed
    )

    locality_weight = 1.0

    # Strong locality suppression:
    # infrastructure tasks should not globally reinforce bakery domains
    if (
        infrastructure_hits >= 2
        and reinforcement_project == "Bakery Operations and Supplies"
    ):
        locality_weight *= 0.35

    # Prevent generic household pull on infrastructure tasks
    if (
        infrastructure_hits >= 2
        and reinforcement_project
        in GENERIC_OPERATIONAL_DOMAINS
    ):
        locality_weight *= 0.55

    # Allow bakery locality reinforcement only when bakery context exists
    if (
        reinforcement_project == "Bakery Operations and Supplies"
        and bakery_hits == 0
    ):
        locality_weight *= 0.50

    return locality_weight


# ============================================================
# B2 REINFORCEMENT PURITY CONTROLS
# ============================================================

GENERIC_OPERATIONAL_DOMAINS = {
    "Household Cleanup and Maintenance",
    "General Household Operations",
    "Personal Admin",
}

INFRASTRUCTURE_KEYWORDS = {
    "router",
    "network",
    "networking",
    "vlan",
    "wifi",
    "wi-fi",
    "switch",
    "ethernet",
    "rack",
    "ups",
    "raspberry",
    "server",
    "dashboard",
    "monitoring",
    "access point",
    "modem",
}


def calculate_reinforcement_purity_adjustment(
    seed_title,
    reinforcement_project,
    operational_score,
):

    normalized_seed = normalize_text(seed_title)

    infrastructure_hits = sum(
        1
        for keyword in INFRASTRUCTURE_KEYWORDS
        if keyword in normalized_seed
    )

    if reinforcement_project in GENERIC_OPERATIONAL_DOMAINS:
        operational_score -= 0.18

    if infrastructure_hits >= 2:
        operational_score += 0.20

    elif infrastructure_hits == 1:
        operational_score += 0.10

    operational_score = max(0.0, min(1.0, operational_score))

    return operational_score







# ============================================================
# B2 TOPOLOGY TELEMETRY
# ============================================================

NOTION_TOPOLOGY_TELEMETRY_DATABASE_ID = os.getenv(
    "NOTION_TOPOLOGY_TELEMETRY_DATABASE_ID"
)

TOPOLOGY_TELEMETRY_VERSION = "B2_self_segmentation_v1"

MUTED_TELEMETRY_EVENTS = {
    "high_specificity_detected",
    "reinforcement_compatible",
}

def get_telemetry_headers():
    """Build telemetry headers lazily after NOTION_TOKEN is injected."""
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }



def topology_telemetry_enabled():

    enabled = bool(NOTION_TOPOLOGY_TELEMETRY_DATABASE_ID)

    print(
        f"[Telemetry] enabled={enabled} "
        f"db_present={bool(NOTION_TOPOLOGY_TELEMETRY_DATABASE_ID)}"
    )

    return enabled


def log_topology_telemetry_event(
    event_type,
    seed_task,
    top_candidate=None,
    runner_up=None,
    margin=None,
    ambiguous=False,
    cluster_size=None,
    expansion_size=None,
    specificity=None,
    subdomain=None,
    suppressed=False,
    notes=None,
):

    if event_type in MUTED_TELEMETRY_EVENTS:
        return

    print(
        f"[Telemetry Emit Attempt] "
        f"event_type={event_type} "
        f"seed={seed_task[:60]}"
    )

    if not topology_telemetry_enabled():

        print("[Telemetry] disabled — skipping emit")

        return

    try:

        properties = {
            "Timestamp": {
                "date": {
                    "start": datetime.now(timezone.utc).isoformat()
                }
            },
            "Seed Task": {
                "title": [
                    {
                        "text": {
                            "content": seed_task[:200]
                        }
                    }
                ]
            },
            "Telemetry Version": {
                "select": {
                    "name": TOPOLOGY_TELEMETRY_VERSION
                }
            },
            "Event Type": {
                "select": {
                    "name": event_type
                }
            },
            "Ambiguous": {
                "checkbox": bool(ambiguous)
            },
            "Suppressed": {
                "checkbox": bool(suppressed)
            },
        }

        if top_candidate:
            properties["Top Candidate"] = {
                "rich_text": [
                    {
                        "text": {
                            "content": str(top_candidate)[:200]
                        }
                    }
                ]
            }

        if runner_up:
            properties["Runner Up"] = {
                "rich_text": [
                    {
                        "text": {
                            "content": str(runner_up)[:200]
                        }
                    }
                ]
            }

        if margin is not None:
            properties["Margin"] = {
                "number": round(float(margin), 4)
            }

        if cluster_size is not None:
            properties["Cluster Size"] = {
                "number": int(cluster_size)
            }

        if expansion_size is not None:
            properties["Expansion Size"] = {
                "number": int(expansion_size)
            }

        if specificity is not None:
            properties["Specificity"] = {
                "number": int(specificity)
            }

        if subdomain:
            properties["Subdomain"] = {
                "select": {
                    "name": str(subdomain)
                }
            }

        if notes:
            properties["Notes"] = {
                "rich_text": [
                    {
                        "text": {
                            "content": str(notes)[:1000]
                        }
                    }
                ]
            }

        print(
            "[Telemetry] writing event to Notion",
            event_type,
        )

        response = requests.post(
            "https://api.notion.com/v1/pages",
            headers=get_telemetry_headers(),
            json={
                "parent": {
                    "database_id": (
                        NOTION_TOPOLOGY_TELEMETRY_DATABASE_ID
                    )
                },
                "properties": properties,
            },
            timeout=15,
        )

        print(
            "[Telemetry] notion_status=",
            response.status_code,
        )

        if response.status_code >= 300:

            print(
                "[Telemetry] notion_response=",
                response.text[:1000],
            )

    except Exception as e:

        print(
            "[Topology Telemetry Error]",
            str(e),
        )


# ============================================================
# B2 NEIGHBORHOOD SELF-SEGMENTATION
# ============================================================

INFRASTRUCTURE_SUBDOMAINS = {
    "network_core": {
        "router",
        "vlan",
        "subnet",
        "switch",
        "dns",
        "dhcp",
        "firewall",
        "ethernet",
        "iot",
    },
    "monitoring": {
        "monitoring",
        "dashboard",
        "raspberry",
        "uptime",
        "metrics",
        "grafana",
    },
    "physical_infrastructure": {
        "ups",
        "rack",
        "power",
        "backup",
        "mount",
        "battery",
        "coverage",
        "wifi",
        "wi-fi",
    },
}


def detect_infrastructure_subdomain(
    task_title,
):

    tokens = get_cached_normalized_tokens(task_title)

    best_match = None
    best_score = 0

    for subdomain, vocabulary in INFRASTRUCTURE_SUBDOMAINS.items():

        score = len(tokens & vocabulary)

        if score > best_score:
            best_match = subdomain
            best_score = score

    if best_match:

        log_topology_telemetry_event(
            event_type="subdomain_detected",
            seed_task=task_title,
            subdomain=best_match,
            notes="Infrastructure subdomain classified",
        )

    return best_match


def calculate_subdomain_topology_affinity(
    seed_title,
    candidate_title,
):

    seed_subdomain = detect_infrastructure_subdomain(seed_title)
    candidate_subdomain = detect_infrastructure_subdomain(candidate_title)

    if not seed_subdomain or not candidate_subdomain:
        return 1.0

    if seed_subdomain == candidate_subdomain:
        return 1.45

    # connected but distinct infrastructure neighborhoods
    return 1.10


# ============================================================
# B2 INFRASTRUCTURE NEIGHBORHOOD DENSIFICATION
# ============================================================

INFRASTRUCTURE_COHESION_TERMS = {
    "vlan",
    "iot",
    "router",
    "network",
    "networking",
    "wifi",
    "wi-fi",
    "raspberry",
    "ups",
    "monitoring",
    "dashboard",
    "switch",
    "ethernet",
    "rack",
    "subnet",
    "dns",
    "dhcp",
    "firewall",
    "coverage",
}


def calculate_infrastructure_neighborhood_cohesion(
    seed_title,
    candidate_title,
):

    seed_tokens = get_cached_normalized_tokens(seed_title)
    candidate_tokens = get_cached_normalized_tokens(candidate_title)

    shared_infrastructure_terms = (
        seed_tokens
        & candidate_tokens
        & INFRASTRUCTURE_COHESION_TERMS
    )

    cohesion_strength = len(shared_infrastructure_terms)

    if cohesion_strength >= 3:
        return 1.60

    if cohesion_strength == 2:
        return 1.35

    if cohesion_strength == 1:
        return 1.15

    return 1.0


# ============================================================
# B2 LOCAL PROJECT TOPOLOGY RECONSTRUCTION
# ============================================================

LOCAL_PROJECT_REINFORCEMENT_RADIUS = 0.25


def calculate_local_project_topology_bias(
    seed_title,
    candidate_title,
    candidate_project=None,
):

    seed_tokens = get_cached_normalized_tokens(seed_title)
    candidate_tokens = get_cached_normalized_tokens(candidate_title)

    overlap = seed_tokens & candidate_tokens

    infrastructure_overlap = sum(
        1
        for token in overlap
        if token in INFRASTRUCTURE_KEYWORDS
    )

    bias = 1.0

    # Strong reinforcement for infrastructure-local overlap
    if infrastructure_overlap >= 2:
        bias *= 1.45

    elif infrastructure_overlap == 1:
        bias *= 1.15

    # Penalize generic bakery bleed-through for infra tasks
    infrastructure_seed = any(
        token in INFRASTRUCTURE_KEYWORDS
        for token in seed_tokens
    )

    bakery_candidate = False

    if candidate_project:
        bakery_candidate = (
            "bakery" in normalize_text(candidate_project)
        )

    if (
        infrastructure_seed
        and bakery_candidate
        and infrastructure_overlap == 0
    ):
        bias *= 0.35

    return bias


# ============================================================
# B2 MERGE TOPOLOGY HYGIENE
# ============================================================

GENERIC_OPERATIONAL_TOKENS = {
    "configure",
    "create",
    "install",
    "update",
    "check",
    "review",
    "test",
    "schedule",
    "maintenance",
    "equipment",
    "system",
    "supplies",
    "support",
    "operations",
    "setup",
    "task",
}


def calculate_merge_topology_hygiene(
    seed_title,
    candidate_title,
):

    seed_tokens = get_cached_normalized_tokens(seed_title)
    candidate_tokens = get_cached_normalized_tokens(candidate_title)

    meaningful_seed_tokens = {
        token
        for token in seed_tokens
        if token not in GENERIC_OPERATIONAL_TOKENS
    }

    meaningful_candidate_tokens = {
        token
        for token in candidate_tokens
        if token not in GENERIC_OPERATIONAL_TOKENS
    }

    overlap = (
        meaningful_seed_tokens
        & meaningful_candidate_tokens
    )

    overlap_score = len(overlap)

    infrastructure_overlap = sum(
        1
        for token in overlap
        if token in INFRASTRUCTURE_KEYWORDS
    )

    # Strong infrastructure reinforcement
    if infrastructure_overlap >= 2:
        return 1.35

    # Reject weak generic overlap
    if overlap_score <= 1:
        return 0.25

    # Mild suppression for weakly related merges
    if overlap_score == 2:
        return 0.60

    return 1.0


# ============================================================
# OPERATIONAL ANALOGY DISCOVERY
# ============================================================

OPERATIONAL_ANALOGY_MIN_SCORE = 0.12


def calculate_operational_analogy_score(
    seed_title,
    candidate_title,
):

    seed_tokens = get_cached_normalized_tokens(seed_title)

    candidate_tokens = get_cached_normalized_tokens(candidate_title)

    if not seed_tokens or not candidate_tokens:
        return 0.0

    direct_overlap = (
        len(seed_tokens & candidate_tokens)
        / max(
            len(seed_tokens),
            len(candidate_tokens),
        )
    )

    infrastructure_terms = {

        "network",
        "wifi",
        "wireless",
        "router",
        "switch",
        "vlan",
        "rack",
        "ethernet",
        "infrastructure",
        "backup",
        "failover",
        "monitoring",
        "firmware",
        "coverage",
        "ups",
        "modem",
    }

    infrastructure_overlap = len(
        (
            seed_tokens
            & candidate_tokens
            & infrastructure_terms
        )
    )

    analogy_bonus = (
        infrastructure_overlap * 0.10
    )

    return round(
        direct_overlap + analogy_bonus,
        2,
    )


def discover_operationally_related_tasks(
    seed_title,
    open_tasks,
):

    analogical_matches = []

    for task in open_tasks or []:

        title = get_title(task)

        if not title:
            continue

        if title == seed_title:
            continue

        analogy_score = (
            calculate_operational_analogy_score(
                seed_title,
                title,
            )
        )

        if analogy_score >= OPERATIONAL_ANALOGY_MIN_SCORE:

            analogical_matches.append(
                (
                    analogy_score,
                    task,
                )
            )

    analogical_matches.sort(
        reverse=True,
        key=lambda x: x[0],
    )

    discovered = [
        task
        for _, task in analogical_matches[:10]
    ]

    if discovered:

        b2_log(
            "[Operational Analogy Discovery] "
            f"{seed_title} "
            f"→ {len(discovered)} analogical neighbors"
        )

    return discovered



# ============================================================
# EXPLORATORY CANDIDATE ADMISSION
# ============================================================

EXPLORATORY_CANDIDATE_ADMISSION_THRESHOLD = 2


def should_allow_exploratory_candidate(
    seed_title,
    related_candidates,
    latent_cluster,
):

    related_count = len(
        related_candidates or []
    )

    latent_count = len(
        latent_cluster.get(
            "related_titles",
            []
        )
    )

    # Allow weak exploratory operational domains
    # to enter downstream ontology evaluation.
    if (
        related_count >= EXPLORATORY_CANDIDATE_ADMISSION_THRESHOLD
        or latent_count >= EXPLORATORY_CANDIDATE_ADMISSION_THRESHOLD
    ):

        b2_log(
            "[Exploratory Candidate Admission] "
            f"{seed_title} "
            f"(related={related_count}, "
            f"latent={latent_count})"
        )

        return True

    return False





# ============================================================
# B2 — OPERATIONAL FIELD DYNAMICS
# ============================================================

OPERATIONAL_FIELD_MIN_REINFORCEMENT_COUNT = 2
OPERATIONAL_FIELD_MAX_REINFORCEMENT_BONUS = 0.35
OPERATIONAL_TEMPORAL_HALF_LIFE_DAYS = 45


def calculate_temporal_recency_weight(task):
    """Return a lightweight recency multiplier for operational reinforcement.

    Recent operational work should reinforce more strongly than stale domains,
    while still preserving persistent infrastructure attractors over time.
    """
    if not task:
        return 0.50

    created_time = task.get("created_time")

    if not created_time:
        return 0.50

    try:
        created = datetime.fromisoformat(
            created_time.replace("Z", "+00:00")
        )

        now = datetime.now(timezone.utc)

        age_days = max(
            (now - created).days,
            0,
        )

    except Exception:
        return 0.50

    if age_days <= 7:
        return 1.00

    if age_days <= 30:
        return 0.85

    if age_days <= OPERATIONAL_TEMPORAL_HALF_LIFE_DAYS:
        return 0.70

    if age_days <= 120:
        return 0.55

    return 0.40


def build_operational_field_strength_index(open_tasks):
    """Build lightweight reinforcement-strength metrics for operational fields."""
    field_strength = {}

    for task in open_tasks or []:

        props = task.get("properties", {}) if task else {}



        project_name = get_rich_text_plain_value(


            props,


            SUGGESTED_PROJECT_PROPERTY,


        )



        if not project_name:



            relation_ids = get_relation_ids(


                props,


                TASK_PROJECT_RELATION_PROPERTY,


            )



            if relation_ids:


                project_name = "Linked Operational Project"

        if not project_name:
            continue

        field_strength.setdefault(
            project_name,
            {
                "count": 0,
                "recent_weight": 0.0,
            },
        )

        field_strength[project_name]["count"] += 1

        field_strength[project_name]["recent_weight"] += (
            calculate_temporal_recency_weight(task)
        )

    return field_strength


def calculate_operational_field_strength(
    project_name,
    field_strength_index,
):
    """Return normalized reinforcement trust for a persistent operational field."""
    if not project_name:
        return 0.0

    stats = (
        field_strength_index or {}
    ).get(
        project_name,
        {},
    )

    count = stats.get(
        "count",
        0,
    )

    recent_weight = stats.get(
        "recent_weight",
        0.0,
    )

    if count < OPERATIONAL_FIELD_MIN_REINFORCEMENT_COUNT:
        return 0.15

    reinforcement_bonus = min(
        recent_weight * 0.04,
        OPERATIONAL_FIELD_MAX_REINFORCEMENT_BONUS,
    )

    return round(
        min(
            0.25 + reinforcement_bonus,
            1.0,
        ),
        2,
    )


def build_operational_field_observability_snapshot(
    seed_title,
    operational_inference,
    field_strength,
    ontology_confidence=None,
):
    """Emit structured reinforcement diagnostics for B2 observability."""
    matched_project = operational_inference.get(
        "matched_project"
    )

    operational_score = operational_inference.get(
        "score",
        0.0,
    )

    print(
        "[Operational Field Dynamics]"
    )

    print(
        f"  seed={seed_title}"
    )

    print(
        f"  matched_project={matched_project}"
    )

    print(
        f"  operational_score={operational_score:.2f}"
    )

    print(
        f"  field_strength={field_strength:.2f}"
    )

    if ontology_confidence is not None:

        print(
            f"  ontology_confidence={ontology_confidence:.2f}"
        )


# ============================================================
# EMERGENT DOMAIN TRUST SCORING
# ============================================================

EMERGENT_DOMAIN_TRUST_THRESHOLD = 0.60


def calculate_emergent_domain_trust(
    latent_cluster,
    operational_inference,
):

    trust = 0.0

    cluster_size = len(
        latent_cluster.get(
            "related_titles",
            []
        )
    )

    trust += min(
        cluster_size * 0.08,
        0.40,
    )

    operational_score = operational_inference.get(
        "score",
        0.0,
    )

    # Weak analogical fit increases
    # pressure for true ontology emergence
    if operational_score < 0.35:
        trust += 0.25

    elif operational_score < 0.50:
        trust += 0.15

    # Persistent unresolved operational work
    # implies latent ontology pressure
    if cluster_size >= 5:
        trust += 0.20

    return round(
        min(trust, 1.0),
        2,
    )


def should_allow_emergent_domain(
    latent_cluster,
    operational_inference,
):

    trust = calculate_emergent_domain_trust(
        latent_cluster,
        operational_inference,
    )

    return (
        trust >= EMERGENT_DOMAIN_TRUST_THRESHOLD,
        trust,
    )



# ============================================================
# LATENT OPERATIONAL MEMORY
# ============================================================

LATENT_OPERATIONAL_MEMORY_THRESHOLD = 0.18
LATENT_OPERATIONAL_MIN_TASKS = 3


def build_latent_operational_memory(
    open_tasks,
):

    latent_memory = {}

    for task in open_tasks or []:

        title = get_title(task)

        if not title:
            continue

        props = task.get("properties", {})

        linked_projects = get_relation_ids(
            props,
            TASK_PROJECT_RELATION_PROPERTY,
        )

        suggested_project = get_rich_text_plain_value(
            props,
            SUGGESTED_PROJECT_PROPERTY,
        )

        # Only use unresolved operational work
        if linked_projects or suggested_project:
            continue

        tokens = set(
            onr.normalize_tokens(title)
        )

        if len(tokens) < 2:
            continue

        latent_memory[title] = tokens

    return latent_memory


def infer_latent_operational_cluster(
    seed_title,
    latent_memory,
):

    seed_tokens = get_cached_normalized_tokens(seed_title)

    related_titles = []

    for title, tokens in latent_memory.items():

        overlap = (
            len(seed_tokens & tokens)
            / max(
                len(seed_tokens),
                len(tokens),
            )
        )

        if overlap >= LATENT_OPERATIONAL_MEMORY_THRESHOLD:

            related_titles.append(
                (overlap, title)
            )

    related_titles.sort(
        reverse=True,
    )

    if len(related_titles) < LATENT_OPERATIONAL_MIN_TASKS:

        return {
            "should_emerge": False,
            "related_titles": [],
        }

    return {

        "should_emerge": True,

        "related_titles": [
            title
            for _, title in related_titles
        ],
    }



def build_operational_memory_from_tasks(tasks):
    """Build lightweight operational memory graph from open tasks."""

    operational_tasks = []

    for task in tasks or []:

        title = get_title(task)

        props = task.get("properties", {}) if task else {}

        project_name = get_rich_text_plain_value(
            props,
            SUGGESTED_PROJECT_PROPERTY,
        )

        if not project_name:

            relation_ids = get_relation_ids(
                props,
                TASK_PROJECT_RELATION_PROPERTY,
            )

            if relation_ids:
                project_name = "Linked Operational Project"

        if not title or not project_name:
            continue

        operational_tasks.append({
            "title": title,
            "project": project_name,
        })

    return onr.build_operational_neighbors(
        operational_tasks
    )



def find_related_task_candidates(seed_task, open_tasks):
    """Find lexically plausible related tasks for one seed task."""
    seed_id = seed_task.get("id")
    seed_title = get_title(seed_task)
    scored = []

    for task in open_tasks:
        if task.get("id") == seed_id:
            continue

        title = get_title(task)
        if not title or title.lower().startswith("clarify next action:"):
            continue

        # Avoid suggesting the child steps of the seed itself as project peers.
        if get_parent_task_id(task) == seed_id:
            continue

        score = project_relation_score(seed_title, title)
        if score <= 0:
            continue

        scored.append({
            "task": task,
            "title": title,
            "score": score,
        })

    scored.sort(key=lambda item: (-item["score"], item["title"].lower()))
    return scored[:globals().get('PROJECT_CANDIDATE_MAX_RELATED_TASKS', 8)]


def ask_ai_project_candidate(seed_title, related_candidates):
    """Ask AI whether related task candidates suggest a real project.

    Returns a dict:
    {
      "should_group": bool,
      "project_name": str,
      "confidence": float,
      "reason": str,
      "related_titles": list[str]
    }
    """
    if not related_candidates:
        return {
            "should_group": False,
            "project_name": "",
            "confidence": 0.0,
            "reason": "No related candidates found.",
            "related_titles": [],
        }

    candidate_lines = "\n".join(
        f"- {item['title']} (candidate score {item['score']:.2f})"
        for item in related_candidates
    )

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=f"""Review whether these tasks likely belong to the same project.

Return ONLY raw JSON with this shape:
{{
  "should_group": true,
  "project_name": "...",
  "confidence": 0.0,
  "reason": "...",
  "related_titles": ["..."]
}}

Definitions:
- A project is a shared outcome, external commitment, or durable operational domain that benefits from grouping tasks.
- Same person, same broad area, same ingredient, same loaf, same formula, or same verb is not enough by itself.
- Prefer fewer, broader, operationally meaningful projects over narrow micro-projects.
- Prefer conservative grouping. If unsure, set should_group false.
- Do not invent details.
- Project name should be short, human-readable, and outcome-based.
- Prefer one of the preferred project names below when one fits cleanly.
- If the preferred names do not fit, you may propose a broad project name only when the tasks form a dense cluster around the same named thing, responsibility, workflow, or outcome.
- Project names should represent a durable area of responsibility, ongoing initiative, or meaningful outcome — not a single action, implementation detail, or temporary task grouping.
- Good project names are broad enough to contain multiple related tasks, stable over time, understandable outside the immediate context, and oriented around an enduring responsibility, workflow, or outcome.
- Avoid project names that are implementation-specific, tied to a single task, overly narrow, temporary, phrased like a one-time action, or based only on shared nouns in the task titles.
- The project name should be something a human would naturally use to organize ongoing work.
- Bad project names: Seed Bread Preparation, Sourdough Starter Maintenance, Bread Tasks, Flour Tasks, Recipe Sharing, Context Extraction Implementation, Incremental Append Mode.
- related_titles must be selected only from the candidate list below.

Preferred project names when they fit:
- School Bread Program
- Weekly Bakery Production
- Bakery Operations and Supplies
- Recipe and Documentation Management
- Workshops and Teaching
- Household Cleanup and Maintenance
- Tax Preparation

Bakery-specific rules:
- Do NOT create projects based only on bread names, flour/grain names, starter/levain, seeds, inclusions, soakers, dough stages, or recipe names.
- Group bakery tasks by operational outcome instead: school fulfillment, weekly production, supplies/inventory/equipment, recipe/documentation, or workshops/teaching.
- If several bakery tasks merely support the same production cycle, prefer Weekly Bakery Production.
- If tasks involve supplies, labels, packaging, inventory, equipment, or purchasing, prefer Bakery Operations and Supplies.
- If tasks involve sending, posting, transcribing, or maintaining recipes/sheets/guides, prefer Recipe and Documentation Management.
- Suppress the candidate if the best name would be based only on a product, ingredient, flour, grain, dough stage, or recipe title.
- The project name must help decide what done means.

Seed task:
{seed_title}

Candidate related tasks:
{candidate_lines}
"""
        )

        import json

        raw = response.output_text.strip()
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not match:
            print("AI project candidate returned non-JSON:", raw)
            return {
                "should_group": False,
                "project_name": "",
                "confidence": 0.0,
                "reason": "AI returned non-JSON.",
                "related_titles": [],
            }

        result = json.loads(match.group(0))
        candidate_titles = {item["title"] for item in related_candidates}
        related_titles = [
            str(title).strip()
            for title in result.get("related_titles", [])
            if str(title).strip() in candidate_titles
        ]

        return {
            "should_group": bool(result.get("should_group", False)),
            "project_name": str(result.get("project_name", "")).strip(),
            "confidence": float(result.get("confidence", 0.0) or 0.0),
            "reason": str(result.get("reason", "")).strip(),
            "related_titles": related_titles,
        }

    except Exception as e:
        print("AI project candidate detection failed:", e)
        return {
            "should_group": False,
            "project_name": "",
            "confidence": 0.0,
            "reason": f"AI project candidate detection failed: {e}",
            "related_titles": [],
        }





def build_task_lookup_by_title(tasks):
    """Map normalized task titles to task pages for project-candidate expansion."""
    lookup = {}
    for task in tasks or []:
        title = get_title(task)
        if title:
            lookup[normalize(title)] = task
    return lookup


def child_tasks_for_parent(parent_task, open_tasks):
    """Return open child tasks linked to a parent task, ordered by Step Order."""
    if not parent_task:
        return []

    parent_id = parent_task.get("id")
    children = [
        task for task in (open_tasks or [])
        if get_parent_task_id(task) == parent_id
    ]

    return sorted(
        children,
        key=lambda task: (
            get_step_order(task) is None,
            get_step_order(task) if get_step_order(task) is not None else 9999,
            task.get("created_time", ""),
            get_title(task).lower(),
        ),
    )


def expand_project_candidate_related_titles(result, open_tasks):
    """Expand related breakdown parents into their child subtasks.

    The AI chooses project-related titles. If one chosen title is a breakdown
    parent, all open child tasks structurally linked through Parent Task are
    included as inherited project context. This is review-only and does not
    change task relations.
    """
    related_titles = [
        str(title).strip()
        for title in result.get("related_titles", [])
        if str(title).strip()
    ]

    if not related_titles:
        result["related_titles"] = []
        result["expanded_related_titles"] = []
        return result

    title_lookup = build_task_lookup_by_title(open_tasks)
    expanded = []
    seen = set()

    def add_title(title, inherited_from=None):
        title = str(title or "").strip()
        if not title:
            return
        key = normalize(title)
        if key in seen:
            return
        seen.add(key)
        expanded.append({
            "title": title,
            "inherited_from": inherited_from,
        })

    for title in related_titles:
        add_title(title)
        task = title_lookup.get(normalize(title))

        if not task:
            continue

        for child in child_tasks_for_parent(task, open_tasks):
            add_title(get_title(child), inherited_from=title)

    result["related_titles"] = [item["title"] for item in expanded]
    result["expanded_related_titles"] = expanded
    return result



PROJECT_APPROVED_NAMES = set(PROJECT_CATEGORY_RULES.keys())

PROJECT_UNHELPFUL_NAME_TOKENS = PROJECT_LOW_VALUE_DOMAIN_TOKENS | {
    "maintenance", "preparation", "sharing", "management", "tasks",
    "task", "project", "misc", "general", "operations", "workflow",
}

PROJECT_UNHELPFUL_EXACT_NAMES = {
    "bakery", "bread", "bread tasks", "bakery tasks", "flour tasks",
    "seed bread preparation", "sourdough starter maintenance",
    "khorasan bread recipe sharing", "recipe sharing",
}

# Generic emerging project support. This deliberately does NOT add
# AIOS, Notion, or any other specific project to PROJECT_CATEGORY_RULES.
# Instead, it allows a dense cluster around the same named thing/responsibility
# to pass validation when the suggested name is broad, durable, and useful for
# organizing ongoing work.
PROJECT_ENTITY_STOPWORDS = {
    "chatgpt", "google", "apple", "siri", "notion", "python",
}

PROJECT_SYSTEM_INTENT_TOKENS = {
    "system", "systems", "software", "app", "code", "script", "scripts",
    "automation", "automations", "pipeline", "pipelines", "workflow",
    "workflows", "database", "databases", "module", "modules",
    "modular", "maintainable", "maintainability", "refactor", "architecture",
    "implement", "implementation", "feature", "features", "enhancement",
    "enhancements", "improve", "improvement", "improvements", "evolve",
    "context", "extraction", "incremental", "append", "parent", "child",
    "awareness", "deferring", "defer", "candidate", "candidates",
    "breakdown", "completion", "outcome", "review", "button",
}

PROJECT_BROAD_SYSTEM_NAME_TOKENS = {
    "system", "systems", "development", "improvement", "improvements",
    "enhancement", "enhancements", "maintainability", "maintenance",
    "architecture", "refactor", "workflow", "workflows", "automation",
    "automations", "platform", "infrastructure", "evolution", "initiative",
    "initiatives", "program", "programs", "responsibility", "responsibilities",
    "operations", "management",
}


def project_name_tokens(project_name):
    return set(words_in(project_name or ""))


def is_approved_project_name(project_name):
    return str(project_name or "").strip() in PROJECT_APPROVED_NAMES


def distinctive_project_entity_tokens(title):
    """Return candidate system/product/entity tokens for emerging projects.

    These tokens are not approved project names. They are just evidence that a
    cluster is about the same named thing. Generic tool names such as ChatGPT
    are excluded so captures like "Ask ChatGPT..." do not become the project
    anchor.
    """
    tokens = set()
    for token in project_meaningful_tokens(title):
        if len(token) < 4:
            continue
        if token in PROJECT_ENTITY_STOPWORDS:
            continue
        if token in PROJECT_SYSTEM_INTENT_TOKENS:
            continue
        tokens.add(token)
    return tokens


def project_system_intent_score(title):
    """Count generic system-improvement signals in one title."""
    return len(set(words_in(title)) & PROJECT_SYSTEM_INTENT_TOKENS)


def shared_distinctive_project_entities(titles, minimum_count=3):
    """Return distinctive entity tokens appearing in at least minimum_count titles."""
    counts = {}
    for title in titles or []:
        for token in distinctive_project_entity_tokens(title):
            counts[token] = counts.get(token, 0) + 1
    return {token for token, count in counts.items() if count >= minimum_count}


def is_broad_emerging_system_project_name(project_name, shared_entities):
    """Return True for broad non-approved names anchored to a shared entity."""
    tokens = project_name_tokens(project_name)
    if not tokens or not shared_entities:
        return False

    # The suggested name should include the named system/product itself. This
    # prevents narrow feature names like "Context Extraction Implementation"
    # from passing just because the related tasks happen to mention one system.
    if not (tokens & shared_entities):
        return False

    return bool(tokens & PROJECT_BROAD_SYSTEM_NAME_TOKENS)


def is_emerging_system_project_candidate(seed_title, result):
    """Return True for dense, named-system clusters without approved names.

    This is the generic escape hatch for projects such as a named local app,
    script, or automation system. It intentionally requires all of these:
    - at least three titles in the cluster, including the seed;
    - a distinctive shared entity token in those titles;
    - system/improvement intent in at least two titles;
    - a broad project name anchored to that shared entity.
    """
    related_titles = result.get("related_titles", []) or []
    titles = [seed_title] + related_titles

    if len(titles) < 3:
        return False

    shared_entities = shared_distinctive_project_entities(titles, minimum_count=3)
    if not shared_entities:
        return False

    system_intent_titles = sum(
        1 for title in titles
        if project_system_intent_score(title) > 0
    )
    if system_intent_titles < 2:
        return False

    return is_broad_emerging_system_project_name(
        result.get("project_name", ""),
        shared_entities,
    )



def is_weak_project_name(project_name):

    emergent_safe_domains = [
        "Home Networking and Infrastructure",
        "Photography and Media Workflow",
    ]

    if project_name in emergent_safe_domains:
        return False

    weak_words = [
        "stuff",
        "things",
        "misc",
        "general",
        "various",
    ]

    lowered = str(project_name or "").lower()

    for word in weak_words:

        if word in lowered:
            return True

    return False

def dominant_project_categories(titles):
    """Return category labels that appear across at least two task titles."""
    counts = {}
    for title in titles or []:
        for label in set(project_category_labels(title)):
            counts[label] = counts.get(label, 0) + 1

    return {label for label, count in counts.items() if count >= 2}


def project_candidate_context_gate(seed_title, result):
    """Return (ok, reason) for approved project names that need context.

    This is deliberately not a blanket conservative gate. It only catches known
    keyword traps: bank/money should not imply Tax Preparation, and Costco/food
    storage should not imply Bakery Operations and Supplies. Stronger operational
    signals still pass normally.
    """
    project_name = result.get("project_name", "")
    titles = [seed_title] + (result.get("related_titles", []) or [])
    all_tokens = set()
    for title in titles:
        all_tokens |= set(words_in(title))

    if project_name == "Tax Preparation":
        if not (all_tokens & PROJECT_TAX_CORE_TOKENS):
            return False, "Tax Preparation requires tax/accountant/CRA/return/receipt context; bank or money alone is weak."

    if project_name == "Bakery Operations and Supplies":
        has_bakery_ops = bool(all_tokens & PROJECT_BAKERY_OPS_CORE_TOKENS)
        personal_food_storage = bool(all_tokens & PROJECT_PERSONAL_FOOD_TOKENS) and not has_bakery_ops
        if personal_food_storage:
            return False, "Household food-storage task; Costco alone is not a bakery-operations signal."
        if not has_bakery_ops:
            return False, "Bakery Operations and Supplies requires bakery, inventory, packaging, equipment, supply, or order context; Costco alone is weak."

    return True, "Project context is coherent."


def project_candidate_has_operational_coherence(seed_title, result):
    """Return True when the candidate is more than shared topic vocabulary."""
    related_titles = result.get("related_titles", []) or []
    titles = [seed_title] + related_titles
    dominant_categories = dominant_project_categories(titles)
    project_name = result.get("project_name", "")

    if is_approved_project_name(project_name):
        # Approved names still need seed-task evidence for that same operational
        # area. A school/program cluster should not absorb a personal customer
        # order merely because both mention bread/order.
        seed_categories = set(project_category_labels(seed_title))
        return project_name in seed_categories and project_name in dominant_categories

    if is_emerging_system_project_candidate(seed_title, result):
        return True

    tokens_by_title = [set(words_in(title)) for title in titles]
    high_value_counts = {}
    for tokens in tokens_by_title:
        for token in tokens & PROJECT_HIGH_VALUE_TOKENS:
            high_value_counts[token] = high_value_counts.get(token, 0) + 1

    return any(count >= 2 for count in high_value_counts.values())




def reinforcement_strengthens_emergent_ontology(
    reinforcement_candidate,
    emergent_project,
):
    """Determine whether reinforcement truly strengthens
    operational ontology structure rather than merely
    sharing weak semantic overlap.
    """

    if not reinforcement_candidate:
        return False

    if not emergent_project:
        return True

    reinforcement_tokens = set(
        onr.normalize_tokens(
            reinforcement_candidate
        )
    )

    emergent_tokens = set(
        onr.normalize_tokens(
            emergent_project
        )
    )

    shared_tokens = (
        reinforcement_tokens & emergent_tokens
    )

    weak_semantic_tokens = {
        "home",
        "system",
        "maintenance",
        "operations",
        "infrastructure",
        "management",
        "support",
        "general",
    }

    meaningful_overlap = {
        token
        for token in shared_tokens
        if token not in weak_semantic_tokens
    }

    overlap = len(meaningful_overlap)

    reinforcement_specificity = (
        calculate_operational_specificity(
            reinforcement_candidate
        )
    )

    emergent_specificity = (
        calculate_operational_specificity(
            emergent_project
        )
    )

    specificity_alignment = abs(
        reinforcement_specificity
        - emergent_specificity
    ) <= 4

    reinforcement_is_same_as_emergent = (
        reinforcement_candidate.strip().lower()
        == emergent_project.strip().lower()
    )

    operationally_compatible = (
        (
            overlap >= 2
            and specificity_alignment
        )
        or reinforcement_is_same_as_emergent
    )

    infrastructure_tokens = {
        "network",
        "networking",
        "router",
        "vlan",
        "wifi",
        "wi-fi",
        "ups",
        "raspberry",
        "monitoring",
        "infrastructure",
        "backup",
        "iot",
    }

    infrastructure_signal = (
        len(
            reinforcement_tokens & infrastructure_tokens
        ) >= 1
        or len(
            emergent_tokens & infrastructure_tokens
        ) >= 1
    )

    contaminated_operational_domains = {
        "household cleanup and maintenance",
        "bakery operations and supplies",
    }

    if (
        infrastructure_signal
        and reinforcement_candidate.strip().lower()
        in contaminated_operational_domains
    ):
        operationally_compatible = False

    ontology_confidence_override = (
        emergent_specificity >= 8
        and infrastructure_signal
    )

    if ontology_confidence_override:

        print(
            "[Ontology Crystallization Override] "
            f"{emergent_project}"
        )

        operationally_compatible = False

    print(
        "[Reinforcement Compatibility] "
        f"reinforcement={reinforcement_candidate} "
        f"emergent={emergent_project} "
        f"meaningful_overlap={overlap} "
        f"specificity_alignment={specificity_alignment} "
        f"strengthens={operationally_compatible}"
    )

    return operationally_compatible


def validate_project_candidate(seed_title, result):
    """Return (is_valid, reason) for a review-only project candidate.

    Validation happens after AI and after related-title expansion. The goal is
    conservative suppression: if the suggestion does not look like a durable
    outcome or operational area, do not print or log it.
    """
    project_name = result.get("project_name", "")
    related_titles = result.get("related_titles", []) or []

    if not result.get("should_group"):
        return False, "AI did not recommend grouping."

    if result.get("confidence", 0.0) < globals().get("PROJECT_CANDIDATE_MIN_CONFIDENCE", 0.65):
        return False, "Below project-candidate confidence threshold."

    effective_expansion_size = result.get(
        "effective_expansion_size",
        len(related_titles),
    )

    ontology_override_allowed = result.get(
        "ontology_override_allowed",
        False,
    )

    ontology_confidence = result.get(
        "ontology_confidence",
        0.0,
    )

    operational_specificity = result.get(
        "operational_specificity",
        0,
    )

    sparse_operational_topology = (
        result.get(
            "operational_ontology_detected",
            False,
        )
        and operational_specificity >= 7
        and ontology_confidence >= 0.45
    )

    if sparse_operational_topology:

        print(
            "[Sparse Operational Topology Accepted] "
            f"{seed_title}"
        )

    if (
        effective_expansion_size
        < globals().get(
            "PROJECT_CANDIDATE_MIN_RELATED_AFTER_EXPANSION",
            2,
        )
        and not ontology_override_allowed
    ):

        if sparse_operational_topology:

            print(
                "[Sparse Ontology Admission Override] "
                f"{seed_title}"
            )

            return (
                True,
                "Sparse operational topology accepted "
                "through ontology crystallization override.",
            )

        return (
            False,
            "Not enough related tasks after expansion."
        )

    if ontology_override_allowed:

        print(
            "[ONTOLOGY VALIDATION OVERRIDE] "
            f"confidence={ontology_confidence:.2f}"
        )

        log_topology_telemetry_event(
            event_type="ontology_override",
            seed_task=seed_title,
            specificity=operational_specificity,
            notes=f"Ontology override activated at confidence {ontology_confidence:.2f}",
        )

    emerging_system_candidate = is_emerging_system_project_candidate(seed_title, result)

    if is_weak_project_name(project_name) and not emerging_system_candidate:
        return False, f"Suppressed weak project name: {project_name}"

    if project_candidate_has_domain_drift(seed_title, result):
        return False, "Tasks cross household cleanup and family scheduling domains."

    if is_household_retrieval_task(seed_title):
        return False, "Household retrieval/support task; insufficient evidence for durable project linkage."

    context_ok, context_reason = project_candidate_context_gate(seed_title, result)
    if not context_ok:
        return False, context_reason

    if not project_candidate_has_operational_coherence(seed_title, result):

        if sparse_operational_topology:

            print(
                "[Operational Outcome Override] "
                f"{seed_title}"
            )

            return (
                True,
                "Operational ontology coherence overrides "
                "legacy semantic outcome validation.",
            )

        return False, "Tasks do not share a strong operational outcome."

    return True, "Review-worthy project candidate."


def run_project_candidate_validation_tests():
    """Validate the final project-candidate safety gate without AI or Notion."""
    print("\n🧪 --- RUNNING PROJECT CANDIDATE VALIDATION TESTS ---\n")

    cases = [
        {
            "label": "suppress weak seed-bread micro-project",
            "seed": "Prepare seed bread soaker",
            "result": {
                "should_group": True,
                "project_name": "Seed Bread Preparation",
                "confidence": 0.90,
                "related_titles": [
                    "Mill flour for seed bread",
                    "Mix seed bread dough",
                ],
            },
            "expected": False,
        },
        {
            "label": "suppress household retrieval false positive",
            "seed": "Get large freezer bags from basement",
            "result": {
                "should_group": True,
                "project_name": "Bakery Operations and Supplies",
                "confidence": 0.92,
                "related_titles": [
                    "Take inventory for weekly bake plan",
                    "Source cheaper stickers for bread packaging",
                ],
            },
            "expected": False,
        },
        {
            "label": "allow school bread program",
            "seed": "Slice bread for school breakfast program",
            "result": {
                "should_group": True,
                "project_name": "School Bread Program",
                "confidence": 0.85,
                "related_titles": [
                    "Prepare school bread order",
                    "Email school about bread order",
                ],
            },
            "expected": True,
        },
        {
            "label": "suppress personal bread order from school program",
            "seed": "Order bread for Tammy and Steve",
            "result": {
                "should_group": True,
                "project_name": "School Bread Program",
                "confidence": 0.86,
                "related_titles": [
                    "Prepare school bread order",
                    "Identify the preferred type or flavor of school bread if required",
                    "Contact the bakery or supplier to place the order for the specified quantity",
                ],
            },
            "expected": False,
        },
        {
            "label": "suppress personal-vs-school relation score",
            "seed": "Order bread for Tammy and Steve",
            "result": {
                "should_group": True,
                "project_name": "School Bread Program",
                "confidence": 0.86,
                "related_titles": [
                    "Prepare school bread order",
                    "Email school about bread order",
                ],
            },
            "expected": False,
        },
        {
            "label": "suppress one lonely related task",
            "seed": "Prepare school bread order",
            "result": {
                "should_group": True,
                "project_name": "School Bread Program",
                "confidence": 0.85,
                "related_titles": ["Email school about bread order"],
            },
            "expected": False,
        },
        {
            "label": "allow bakery supplies",
            "seed": "Order Costco bakery supplies",
            "result": {
                "should_group": True,
                "project_name": "Bakery Operations and Supplies",
                "confidence": 0.80,
                "related_titles": [
                    "Check packaging inventory",
                    "Buy bread bags",
                ],
            },
            "expected": True,
        },
        {
            "label": "allow emerging named-thing durable project",
            "seed": "Ask ChatGPT to help evolve AIOS into a maintainable system",
            "result": {
                "should_group": True,
                "project_name": "AIOS Workflow Improvements",
                "confidence": 0.88,
                "related_titles": [
                    "Brainstorm list of enhancements for AIOS",
                    "Ask ChatGPT to break the AIOS code into modules",
                    "Ask ChatGPT to implement Context extraction in AIOS",
                ],
            },
            "expected": True,
        },
        {
            "label": "suppress narrow emerging-system feature name",
            "seed": "Ask ChatGPT to help evolve AIOS into a maintainable system",
            "result": {
                "should_group": True,
                "project_name": "Context Extraction Implementation",
                "confidence": 0.88,
                "related_titles": [
                    "Brainstorm list of enhancements for AIOS",
                    "Ask ChatGPT to break the AIOS code into modules",
                    "Ask ChatGPT to implement Context extraction in AIOS",
                ],
            },
            "expected": False,
        },
        {
            "label": "suppress family calendar as household cleanup",
            "seed": "Ask Janet to add her trip to BC to the family calendar",
            "result": {
                "should_group": True,
                "project_name": "Household Cleanup and Maintenance",
                "confidence": 0.85,
                "related_titles": [
                    "Message family members to ask who can take Mum to appointment with Dr. Lai",
                    "Create a checklist for daily restocking and cleaning tasks",
                    "Inspect pool cleaning tools and repair or replace any damaged equipment",
                    "Take box from living room to recycling",
                    "Wash hand dishes",
                ],
            },
            "expected": False,
        },
        {
            "label": "suppress relation score from family calendar to cleanup chores",
            "seed": "Ask Janet to add her trip to BC to the family calendar",
            "result": {
                "should_group": True,
                "project_name": "Household Cleanup and Maintenance",
                "confidence": 0.85,
                "related_titles": [
                    "Take box from living room to recycling",
                    "Wash hand dishes",
                ],
            },
            "expected": False,
        },
        {
            "label": "suppress bank/money personal errand as tax prep",
            "seed": "Get money for Luz from bank",
            "result": {
                "should_group": True,
                "project_name": "Tax Preparation",
                "confidence": 0.86,
                "related_titles": [
                    "Deposit money at bank",
                    "Transfer money to Luz",
                ],
            },
            "expected": False,
        },
        {
            "label": "allow real tax prep with bank support task",
            "seed": "Download tax receipts from bank",
            "result": {
                "should_group": True,
                "project_name": "Tax Preparation",
                "confidence": 0.86,
                "related_titles": [
                    "Submit tax documents to accountant",
                    "Update tax spreadsheet in Excel",
                ],
            },
            "expected": True,
        },
        {
            "label": "suppress Costco household food as bakery operations",
            "seed": "Freeze chicken from Costco",
            "result": {
                "should_group": True,
                "project_name": "Bakery Operations and Supplies",
                "confidence": 0.86,
                "related_titles": [
                    "Put Costco groceries away",
                    "Freeze extra chicken",
                ],
            },
            "expected": False,
        },
        {
            "label": "allow Costco task when bakery supply context is explicit",
            "seed": "Buy bread bags from Costco",
            "result": {
                "should_group": True,
                "project_name": "Bakery Operations and Supplies",
                "confidence": 0.86,
                "related_titles": [
                    "Check bakery packaging inventory",
                    "Order labels for bread bags",
                ],
            },
            "expected": True,
        },
    ]

    passed = 0
    failed = 0
    for case in cases:
        actual, reason = validate_project_candidate(case["seed"], dict(case["result"]))
        ok = actual == case["expected"]
        if print_test_result(
            ok,
            f"project candidate: {case['label']} → {actual}",
            "" if ok else f"expected {case['expected']} ({reason})",
        ):
            passed += 1
        else:
            failed += 1

    print(f"\nProject candidate validation results: {passed} passed, {failed} failed")
    return failed == 0



def print_project_candidate(seed_title, result):
    """Print one project candidate review item to the run log."""
    print("\n--- PROJECT CANDIDATE ---")
    print("Seed task:", seed_title)
    print("Suggested project:", result.get("project_name") or "")
    print(f"Confidence: {result.get('confidence', 0):.2f}")
    print("Reason:", result.get("reason") or "")
    print("Related tasks:")

    expanded_items = result.get("expanded_related_titles") or [
        {"title": title, "inherited_from": None}
        for title in result.get("related_titles", [])
    ]

    for item in expanded_items:
        title = item.get("title")
        inherited_from = item.get("inherited_from")
        if inherited_from:
            print("   -", title, f"(subtask of {inherited_from})")
        else:
            print(" -", title)


def log_project_candidate(seed_title, result):
    """Write a review-only project candidate to the AI Processing Log."""
    expanded_items = result.get("expanded_related_titles") or [
        {"title": title, "inherited_from": None}
        for title in result.get("related_titles", [])
    ]

    reason_lines = [
        "Review-only project candidate. No project or task relation was changed.",
        "Breakdown parent tasks are expanded to include their open subtasks.",
        f"Suggested project: {result.get('project_name') or ''}",
        f"Reason: {result.get('reason') or ''}",
    ]

    if expanded_items:
        reason_lines.append("Related tasks:")
        for item in expanded_items:
            title = item.get("title")
            inherited_from = item.get("inherited_from")
            if inherited_from:
                reason_lines.append(f"  - {title} (subtask of {inherited_from})")
            else:
                reason_lines.append(f"- {title}")

    logged = log_ai_processing_decision(
        original=seed_title,
        final_task=seed_title,
        action="Project Candidate",
        reason="\n".join(reason_lines),
        review_needed=True,
        confidence=result.get("confidence"),
        source="Project Detector",
        suggested_project=result.get("project_name") or "",
    )

    if logged:
        increment_summary("project_candidate_log_entries")

    return logged


# -----------------------------------------------------------------------------
# Phase 3: Suggested Project + safe Project relation write-back
# -----------------------------------------------------------------------------
# Design:
# - Suggested Project is the review/staging text field on Tasks.
# - Project relation is the canonical structural link.
# - AIOS may set the Project relation only when the suggested project has one
#   unambiguous match in the existing Projects DB.
# - AIOS never creates, renames, merges, deletes, or overwrites project records.
# - Status is the primary active/inactive signal. The legacy Active checkbox is
#   optional and can only include a project when Status is blank; it no longer
#   blocks a project whose Status is Active.


def get_rich_text_plain_value(props, property_name):
    """Return plain text from a Notion rich_text/Text property."""
    prop = props.get(property_name, {}) if props else {}
    rich_text = prop.get("rich_text") or []
    return "".join(rt.get("plain_text", "") for rt in rich_text).strip()


def update_suggested_project_if_needed(task, suggested_project, source="Project Detector"):
    """Write Suggested Project text onto a task when the field is blank.

    This does not create Projects records and does not set the Project relation.
    Existing values are preserved to avoid overwriting manual edits or causing
    label thrash while matching is still being tuned.
    """
    suggested_project = str(suggested_project or "").strip()

    if not task or task.get("dry_run") or not suggested_project:
        return False

    props = task.get("properties", {})
    current_value = get_rich_text_plain_value(props, SUGGESTED_PROJECT_PROPERTY)
    title = get_title(task)

    if current_value:
        if current_value != suggested_project:
            print(f"Suggested Project preserved: {title} already has {current_value!r}; candidate was {suggested_project!r}")
        return False

    if TEST_MODE or DRY_RUN:
        print(f"[DRY RUN] Would set Suggested Project: {title} → {suggested_project}")
        return False

    response = requests.patch(
        f"https://api.notion.com/v1/pages/{task['id']}",
        headers=headers,
        json={"properties": {SUGGESTED_PROJECT_PROPERTY: _notion_rich_text(suggested_project)}},
        timeout=30,
    )

    if response.ok:
        increment_summary("suggested_project_updates")
        print(f"Set Suggested Project: {title} → {suggested_project}")
        return True

    increment_summary("errors")
    print("ERROR setting Suggested Project:", title)
    print(response.status_code, response.text)
    return False


def query_projects_database(page_size=100):
    """Query the Projects database with pagination."""
    if not PROJECTS_DATABASE_ID:
        print(
            "Project relation write-back skipped: PROJECTS_DATABASE_ID is not configured "
            "(also checked PROJECT_DATABASE_ID, NOTION_PROJECTS_DATABASE_ID, and NOTION_PROJECT_DATABASE_ID)."
        )
        return []

    print(f"Querying Projects database: {PROJECTS_DATABASE_ID[:8]}…")
    url = f"https://api.notion.com/v1/databases/{PROJECTS_DATABASE_ID}/query"
    payload = {"page_size": page_size}
    projects = []

    while True:
        response = requests.post(url, headers=headers, json=payload, timeout=30)

        if not response.ok:
            increment_summary("errors")
            print("ERROR querying Projects database")
            print(response.status_code, response.text)
            return projects

        data = response.json()
        projects.extend(data.get("results", []))

        if not data.get("has_more"):
            break

        payload["start_cursor"] = data.get("next_cursor")

    return projects


def normalize_project_status_name(status):
    """Normalize project status text for stable comparisons."""
    return re.sub(r"\s+", " ", str(status or "").strip()).lower()


ACTIVE_PROJECT_STATUS_VALUES_NORMALIZED = {
    normalize_project_status_name(value) for value in ACTIVE_PROJECT_STATUS_VALUES
}
INACTIVE_PROJECT_STATUS_VALUES_NORMALIZED = {
    normalize_project_status_name(value) for value in INACTIVE_PROJECT_STATUS_VALUES
}


def get_project_status_name(project):
    """Return project Status from either Select or Status-shaped Notion fields."""
    props = project.get("properties", {}) if project else {}
    return get_select_or_status_name(props, PROJECT_STATUS_PROPERTY)


def project_active_checkbox_value(project):
    """Return Active checkbox value, or None if the checkbox/property is absent."""
    props = project.get("properties", {}) if project else {}
    prop = props.get(PROJECT_ACTIVE_PROPERTY, {})
    if prop.get("type") == "checkbox":
        return bool(prop.get("checkbox"))
    return None


def is_active_project(project):
    """Return True when a project is eligible for safe auto-linking.

    Status is the primary signal:
    - Active/In Progress/Current/Ongoing => active
    - Completed/Done/Archived/Paused/Someday => inactive

    The optional Active checkbox is only a fallback include when Status is blank.
    It is not required and it no longer blocks Status=Active projects.
    """
    status = get_project_status_name(project)
    status_key = normalize_project_status_name(status)

    if status_key in INACTIVE_PROJECT_STATUS_VALUES_NORMALIZED:
        return False

    if status_key in ACTIVE_PROJECT_STATUS_VALUES_NORMALIZED:
        return True

    active_checkbox = project_active_checkbox_value(project)
    if active_checkbox is True:
        return True

    # Sparse DBs are common, so blank status remains eligible unless the Active
    # checkbox explicitly exists and is unchecked. Unknown non-blank statuses are
    # conservative and skipped until added to ACTIVE_PROJECT_STATUS_VALUES.
    if not status_key:
        return active_checkbox is not False

    return False


def get_active_projects():
    """Return active Projects DB records for Phase 3 matching."""
    projects = query_projects_database()
    active = [project for project in projects if is_active_project(project) and get_title(project)]

    print(f"Loaded active projects: {len(active)}/{len(projects)}")

    if active:
        print("Active projects available for write-back:")
        for project in active[:10]:
            print(" -", get_title(project))
    elif projects:
        print("Project status diagnostics:")
        for project in projects[:10]:
            print(
                " -",
                get_title(project) or project.get("id"),
                f"Status={get_project_status_name(project)!r}",
                f"Active checkbox={project_active_checkbox_value(project)!r}",
            )

    return active


def get_all_projects():
    """Return all Projects DB records for duplicate detection and stub creation."""
    return query_projects_database()


def find_project_by_name(candidate_name, projects):
    """Return an existing project with the same normalized name, active or inactive."""
    candidate_key = normalize(candidate_name or "")
    if not candidate_key:
        return None

    for project in projects or []:
        if normalize(get_title(project)) == candidate_key:
            return project

    return None


def get_project_status_property_type(projects):
    """Infer whether the Projects Status property is select or status shaped."""
    for project in projects or []:
        prop = project.get("properties", {}).get(PROJECT_STATUS_PROPERTY, {})
        prop_type = prop.get("type")
        if prop_type in {"select", "status"}:
            return prop_type

    # Select is easier to create with in sparse / new databases. If the user's
    # Projects DB uses a Notion Status property, the API error will make that
    # visible in the log and PROJECT_STUB_STATUS_VALUE can still be adjusted.
    return "select"


def build_project_stub_properties(project_name, existing_projects=None):
    """Build conservative properties for a new inactive project stub."""
    properties = {
        PROJECT_TITLE_PROPERTY: {
            "title": [{"type": "text", "text": {"content": project_name}}]
        }
    }

    status_value = str(PROJECT_STUB_STATUS_VALUE or "").strip()
    if status_value:
        status_type = get_project_status_property_type(existing_projects)
        if status_type == "status":
            properties[PROJECT_STATUS_PROPERTY] = {"status": {"name": status_value}}
        else:
            properties[PROJECT_STATUS_PROPERTY] = {"select": {"name": status_value}}

    # If an Active checkbox exists, explicitly keep new stubs inactive. If the
    # property does not exist in the database, Notion will reject this write, so
    # only include it when we have seen it on an existing project.
    if any(PROJECT_ACTIVE_PROPERTY in (project.get("properties", {}) or {}) for project in (existing_projects or [])):
        properties[PROJECT_ACTIVE_PROPERTY] = {"checkbox": False}

    return properties


def create_inactive_project_stub_if_missing(
    project_name,
    existing_projects=None,
    source_reason="",
    possible_existing_project=None,
    possible_existing_project_confidence=None,
):
    """Create a new inactive Projects DB row for a missing suggested project.

    This is intentionally separate from relation write-back. Newly-created
    project stubs are review targets, not active projects, so tasks are not
    linked to them automatically until the project is manually activated.
    """
    project_name = str(project_name or "").strip()
    if not project_name:
        return None

    if TEST_MODE or DRY_RUN or not RUN_PROJECT_STUB_CREATION:
        increment_summary("project_record_create_skipped")
        print(f"Project stub creation skipped for {project_name}: test/dry-run/disabled")
        return None

    if not PROJECTS_DATABASE_ID:
        increment_summary("project_record_create_skipped")
        print(f"Project stub creation skipped for {project_name}: PROJECTS_DATABASE_ID is not configured")
        return None

    existing_projects = existing_projects or []
    existing = find_project_by_name(project_name, existing_projects)
    if existing:
        increment_summary("project_record_create_skipped")
        print(f"Project stub preserved: {project_name} already exists with Status={get_project_status_name(existing)!r}")
        return existing

    response = requests.post(
        "https://api.notion.com/v1/pages",
        headers=headers,
        json={
            "parent": {"database_id": PROJECTS_DATABASE_ID},
            "properties": build_project_stub_properties(project_name, existing_projects),
        },
        timeout=30,
    )

    if response.ok:
        project = response.json()
        increment_summary("project_records_created")
        print(f"Created inactive project stub: {project_name} → Status={PROJECT_STUB_STATUS_VALUE!r}")
        log_ai_processing_decision(
            original=project_name,
            final_task=project_name,
            action="Project Created",
            reason=(
                f"Created inactive project stub from Suggested Project. "
                f"Status set to {PROJECT_STUB_STATUS_VALUE!r}; task relation was not set. {source_reason}"
            ),
            review_needed=True,
            confidence=None,
            source="Project Detector",
            suggested_project=project_name,
        )
        return project

    increment_summary("errors")
    print("ERROR creating inactive project stub:", project_name)
    print(response.status_code, response.text)
    return None




def project_similarity_score(candidate_name, project_name):
    """Domain-aware semantic similarity with canonical simplicity bias."""

    if normalize(candidate_name) == normalize(project_name):
        return 1.0

    score = weighted_similarity(
        candidate_name,
        project_name,
    )

    # ========================================================
    # Prefer broader reusable operational domains
    # over implementation-specific variants
    # ========================================================

    simplicity_penalty = canonical_simplicity_bonus(
        project_name
    )

    score -= simplicity_penalty

    return max(0.0, min(score, 1.0))


def project_match_score(candidate_name, project_name):
    """Score a candidate project name against an existing project name."""
    if normalize(candidate_name) == normalize(project_name):
        return 1.0
    return similarity(candidate_name, project_name)


def find_existing_project_match(candidate_name, active_projects):
    """Return (project, score, reason) for one unambiguous strong ACTIVE match.

    ACTIVE projects are privileged execution domains.
    Inactive projects remain semantic memory / governance artifacts.
    """
    candidate_name = str(candidate_name or "").strip()

    if not candidate_name or not active_projects:
        return None, 0.0, "No project candidate or no active projects."

    scored = []

    for project in active_projects:

        project_name = get_title(project)

        score = project_similarity_score(
            candidate_name,
            project_name,
        )

        scored.append(
            (
                score,
                project,
                project_name,
            )
        )

    scored.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    best_score, best_project, best_name = scored[0]

    second_score = (
        scored[1][0]
        if len(scored) > 1 else 0.0
    )

    ACTIVE_PROJECT_THRESHOLD = 0.60

    print(
        "[Project Canonicalization] "
        f"best active match="
        f"{best_name} "
        f"({best_score:.2f})"
    )

    if best_score < ACTIVE_PROJECT_THRESHOLD:

        return (
            None,
            best_score,
            f"Best active project match below threshold: "
            f"{best_name} ({best_score:.2f})."
        )

    if (
        len(scored) > 1
        and (best_score - second_score)
        < PROJECT_LINK_AMBIGUITY_MARGIN
    ):

        return (
            None,
            best_score,
            f"Ambiguous project match: "
            f"{best_name} ({best_score:.2f}) "
            f"vs next ({second_score:.2f})."
        )

    print(
        "[Project Canonicalization] "
        f"reusing ACTIVE project: "
        f"{best_name}"
    )

    return (
        best_project,
        best_score,
        f"Matched existing ACTIVE project: "
        f"{best_name} ({best_score:.2f})."
    )


def task_has_project_relation(task):
    """Return True when the canonical Project relation is already set."""
    return bool(get_relation_ids(task.get("properties", {}), TASK_PROJECT_RELATION_PROPERTY))


def set_project_relation_if_safe(task, project, suggested_project, match_score, source_reason=""):
    """Set the real Project relation only when Phase 3 guardrails pass."""
    if TEST_MODE or DRY_RUN or not RUN_PROJECT_RELATION_WRITEBACK:
        return False

    if not task or task.get("dry_run") or not project:
        return False

    title = get_title(task)
    if not title or title.lower().startswith("clarify next action:"):
        return False

    if task_has_project_relation(task):
        increment_summary("project_relation_skipped")
        print(f"Project relation preserved: {title} already has a project relation")
        return False

    response = requests.patch(
        f"https://api.notion.com/v1/pages/{task['id']}",
        headers=headers,
        json={
            "properties": {
                TASK_PROJECT_RELATION_PROPERTY: {
                    "relation": [{"id": project["id"]}]
                }
            }
        },
        timeout=30,
    )

    if response.ok:
        increment_summary("project_relation_updates")
        project_name = get_title(project)
        print(f"Set Project relation: {title} → {project_name}")
        log_ai_processing_decision(
            original=title,
            final_task=title,
            action="Project Linked",
            reason=f"Linked to existing active project '{project_name}' from Suggested Project '{suggested_project}'. {source_reason}",
            review_needed=False,
            confidence=match_score,
            source="Project Detector",
            suggested_project=suggested_project,
        )
        return True

    increment_summary("errors")
    print("ERROR setting Project relation:", title)
    print(response.status_code, response.text)
    return False


def apply_manual_project_intent(seed_task, project_name, open_tasks, all_projects, active_projects):
    """Honor an explicit Brain Dump [project hint] as authoritative user intent.

    M1.3 keeps manual intent separate from AI Suggested Project values. Tasks
    carrying the same explicit hint in the current run share one review project.
    Existing project rows are reused; a newly created inactive stub is appended
    to the in-memory project list immediately so later tagged tasks cannot create
    duplicates during the same run.
    """
    project_name = str(project_name or "").strip()
    if not seed_task or not project_name:
        return 0

    exact_project = find_project_by_name(project_name, all_projects)
    if exact_project is None:
        exact_project = create_inactive_project_stub_if_missing(
            project_name,
            existing_projects=all_projects,
            source_reason="Explicit project hint in Brain Dump.",
        )
        if exact_project:
            all_projects.append(exact_project)

    active_exact = exact_project if exact_project and is_active_project(exact_project) else None
    review_project = exact_project if exact_project and not is_active_project(exact_project) else None

    tagged_tasks = []
    seen_ids = set()
    for task in [seed_task] + list(globals().get("created_tasks", [])):
        if not task or task.get("id") in seen_ids:
            continue
        explicit_hint = str(task.get("_manual_project_hint") or "").strip()
        if normalize(explicit_hint) != normalize(project_name):
            continue
        seen_ids.add(task.get("id"))
        tagged_tasks.append(task)

    updated_count = 0
    for task in tagged_tasks:
        if active_exact:
            if set_project_relation_if_safe(
                task,
                active_exact,
                project_name,
                1.0,
                "Explicit project hint matched an existing active project exactly.",
            ):
                updated_count += 1
        elif review_project:
            if set_review_project_relation_if_empty(task, review_project, project_name):
                updated_count += 1

    print(
        f"Manual project intent applied: {project_name} → "
        f"{len(tagged_tasks)} tagged task(s); "
        f"project_match={'active' if active_exact else 'review' if review_project else 'none'}"
    )
    log_ai_processing_decision(
        original=get_title(seed_task),
        final_task=get_title(seed_task),
        action="Project Tagged",
        reason=f"Explicit Brain Dump project hint: {project_name}",
        review_needed=active_exact is None,
        confidence=1.0,
        source="Brain Dump",
        suggested_project=project_name,
    )
    return updated_count


def find_existing_project_cluster_match(
    candidate_name,
    candidate_titles,
    project_contexts,
    ai_client,
):
    """Return one strong ACTIVE project match for a fully emerged task cluster.

    This is the final duplicate-project gate before AIOS creates a new
    inactive project stub. Context-building stays outside this helper so the
    semantic matcher does not depend on transitional runtime injection.
    """
    candidate_name = str(candidate_name or "").strip()

    cluster_titles = []
    seen = set()

    for value in candidate_titles or []:
        title = str(value or "").strip()
        key = " ".join(title.lower().split())

        if not title or not key or key in seen:
            continue

        seen.add(key)
        cluster_titles.append(title)

    contexts = [
        context
        for context in (project_contexts or [])
        if context.get("active")
        and str(context.get("project_name") or "").strip()
    ]

    if not candidate_name or not cluster_titles:
        return None, 0.0, "No usable emerged project cluster.", False

    if not contexts:
        return None, 0.0, "No active project contexts available.", False

    if ai_client is None:
        return None, 0.0, "No AI client available for cluster affinity.", False

    project_by_key = {}
    project_lines = []

    for index, context in enumerate(contexts, start=1):
        key = f"P{index:03d}"
        project_by_key[key] = context

        members = "; ".join(
            context.get("member_titles") or []
        ) or "(no current open members)"

        project_lines.append(
            f"{key} | {context['project_name']} | "
            f"current tasks: {members}"
        )

    cluster_text = "\n".join(
        f"- {title}"
        for title in cluster_titles[:25]
    )

    prompt = f"""Determine whether an EMERGED PROJECT CLUSTER is actually part of
an EXISTING ACTIVE project.

Return ONLY raw JSON:

{{
  "match": {{
    "project_key": "P001",
    "confidence": 0.0,
    "reason": "..."
  }}
}}

or:

{{"match": null}}

Rules:
- Existing active projects have priority over creating a duplicate new project.
- Evaluate the candidate using BOTH its proposed project name and the collective meaning of its task cluster.
- Evaluate existing projects using BOTH their names and their current member tasks.
- Match only when both represent substantially the same outcome, responsibility, or coordinated body of work.
- Shared vocabulary or broad topic similarity alone are not enough.
- A narrower implementation-oriented cluster may belong to a broader active project when its tasks clearly advance that same project.
- Do not force a match when the projects could reasonably remain distinct.
- When uncertain, return null.

EMERGED PROJECT:
{candidate_name}

CLUSTER TASKS:
{cluster_text}

EXISTING ACTIVE PROJECTS:
{chr(10).join(project_lines)}
"""

    try:
        response = ai_client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
        )
        data = parse_json_object(
            getattr(response, "output_text", "") or ""
        )
    except Exception as exc:
        print(
            "[PROJECT CLUSTER AFFINITY] AI error:",
            exc,
        )
        return None, 0.0, "Cluster affinity AI call failed.", False

    match = data.get("match")

    if not isinstance(match, dict):
        return None, 0.0, "No strong existing-project cluster match.", False

    project_key = match.get("project_key")

    if project_key not in project_by_key:
        return None, 0.0, "Cluster affinity returned an unknown project.", False

    try:
        confidence = float(
            match.get("confidence") or 0.0
        )
    except (TypeError, ValueError):
        confidence = 0.0

    threshold = globals().get(
        "PROJECT_CLUSTER_AFFINITY_MIN_CONFIDENCE",
        0.88,
    )

    context = project_by_key[project_key]
    project = context["project"]
    project_name = context["project_name"]

    print(
        "[PROJECT CLUSTER AFFINITY] "
        f"{candidate_name} → {project_name} "
        f"({confidence:.2f})"
    )

    if confidence < threshold:
        return (
            project,
            confidence,
            "Best cluster match below confidence threshold: "
            f"{project_name} ({confidence:.2f}).",
            False,
        )

    reason = str(
        match.get("reason") or ""
    ).strip()

    print(
        "[PROJECT CLUSTER AFFINITY] "
        f"Reusing ACTIVE project: {project_name}"
    )

    return (
        project,
        confidence,
        (
            f"Matched emerged cluster to existing ACTIVE project "
            f"{project_name!r} ({confidence:.2f}). "
            f"{reason}"
        ).strip(),
        True,
    )


def apply_project_candidate_writeback(seed_task, result, open_tasks, all_projects, active_projects):
    """Apply Suggested Project and, when safe, the real Project relation.

    Applies to the seed task and any related open tasks that can be found by
    exact title in the local scan set.
    """
    suggested_project = str(result.get("project_name") or "").strip()
    if not suggested_project:
        return 0

    candidate_titles = [get_title(seed_task)]
    candidate_titles.extend(result.get("related_titles") or [])
    candidate_titles.extend(
        item.get("title")
        for item in (result.get("expanded_related_titles") or [])
        if item.get("title")
    )

    possible_existing_project = None
    possible_existing_project_confidence = None

    existing_project = find_project_by_name(
        suggested_project,
        all_projects,
    )

    project, score, reason = find_existing_project_match(
        suggested_project,
        active_projects,
    )

    # Individual task affinity already ran before project emergence.
    # If the completed cluster still appears to imply a new project, give the
    # cluster as a whole one final chance to match an existing active project.
    if not project and not existing_project:
        project_contexts = build_incremental_project_contexts(
            all_projects,
            open_tasks,
        )

        (
            cluster_project,
            cluster_score,
            cluster_reason,
            auto_match,
        ) = find_existing_project_cluster_match(
            suggested_project,
            candidate_titles,
            project_contexts,
            client,
        )

        review_band_min = globals().get(
            "PROJECT_CLUSTER_REVIEW_MIN_CONFIDENCE",
            0.75,
        )

        if auto_match and cluster_project:
            project = cluster_project
            score = cluster_score
            reason = cluster_reason

            # Canonicalize Suggested Project metadata to the existing project
            # rather than preserving the duplicate emerged-project name.
            suggested_project = get_title(project)

        elif (
            cluster_project
            and cluster_score >= review_band_min
        ):
            possible_existing_project = cluster_project
            possible_existing_project_confidence = cluster_score
            reason = cluster_reason

    review_project = None

    if not project and existing_project:
        existing_status = get_project_status_name(existing_project)
        reason = (
            "Suggested project already exists but is not active: "
            f"Status={existing_status!r}."
        )
        review_project = existing_project

    elif not project and not existing_project:
        review_project = create_inactive_project_stub_if_missing(
            suggested_project,
            existing_projects=all_projects,
            source_reason=reason,
            possible_existing_project=possible_existing_project,
            possible_existing_project_confidence=(
                possible_existing_project_confidence
            ),
        )

        if review_project:
            all_projects.append(review_project)

    tasks_by_title = {}

    for task in [seed_task] + list(open_tasks or []):
        title = get_title(task)

        if title:
            tasks_by_title.setdefault(title, task)

    seen_titles = set()
    updated_count = 0
    for title in candidate_titles:
        if not title or title in seen_titles:
            continue
        seen_titles.add(title)

        task = tasks_by_title.get(title)
        if not task:
            continue

        if update_suggested_project_if_needed(task, suggested_project):
            updated_count += 1

        if project:
            if set_project_relation_if_safe(task, project, suggested_project, score, reason):
                updated_count += 1
        elif review_project:
            # M1.2: inactive stubs are explicit review objects. Linking is safe
            # only when the task has no existing Project relation.
            if set_review_project_relation_if_empty(task, review_project, suggested_project):
                updated_count += 1
        else:
            increment_summary("project_relation_skipped")
            if not RUN_PROJECT_RELATION_WRITEBACK:
                skip_reason = "Relation write-back is disabled by RUN_PROJECT_RELATION_WRITEBACK."
            elif not active_projects:
                skip_reason = "No active projects were loaded from the Projects database."
            else:
                skip_reason = reason
            print(f"Project relation write-back skipped for {suggested_project}: {skip_reason}")

    return updated_count


def run_project_relation_writeback_tests():
    """Validate active-project filtering and safe project matching."""
    print("\n🧪 --- RUNNING PROJECT RELATION WRITE-BACK TESTS ---\n")

    def fake_project(project_id, title, status="Active", active=False, status_shape="select"):
        if status_shape == "status":
            status_prop = {"type": "status", "status": {"name": status} if status else None}
        else:
            status_prop = {"type": "select", "select": {"name": status} if status else None}
        return {
            "id": project_id,
            "properties": {
                PROJECT_TITLE_PROPERTY: {"type": "title", "title": [{"plain_text": title}]},
                PROJECT_STATUS_PROPERTY: status_prop,
                PROJECT_ACTIVE_PROPERTY: {"type": "checkbox", "checkbox": active},
            },
        }

    manual_clarification_task = {
        "id": "manual-clarify",
        "_manual_project_hint": "Basement Recovery",
        "properties": {
            TASK_TITLE_PROPERTY: {
                "type": "title",
                "title": [{"plain_text": "Clarify next action: Move furniture from furnace room"}],
            }
        },
    }

    manual_source_ok = is_project_candidate_source_task(manual_clarification_task)
    print(
        ("PASS" if manual_source_ok else "FAIL"),
        "manual project hint remains eligible even if clarification wrapper exists",
    )

    projects = [
        fake_project("p1", "Bakery Operations and Supplies", status="Active", active=False, status_shape="select"),
        fake_project("p2", "Workshops and Teaching", status="Active", active=False, status_shape="status"),
        fake_project("p3", "Archived Thing", status="Completed", active=True, status_shape="select"),
        fake_project("p4", "Checkbox Only Project", status=None, active=True, status_shape="select"),
        fake_project("p5", "Unchecked Blank Project", status=None, active=False, status_shape="select"),
    ]

    active_projects = [p for p in projects if is_active_project(p)]
    checks = [
        (len(active_projects) == 3, "active loader uses Status first and checkbox fallback", f"expected 3 active, got {len(active_projects)}"),
        (find_existing_project_match("Bakery Operations and Supplies", active_projects)[0] is not None, "exact select-status match", "expected match"),
        (find_existing_project_match("Workshops and Teaching", active_projects)[0] is not None, "exact status-shape match", "expected match"),
        (find_existing_project_match("Missing Project", active_projects)[0] is None, "missing project does not match", "expected no match"),
        (find_project_by_name("Archived Thing", projects) is not None, "inactive existing project is detected by name", "expected existing inactive project"),
        (build_project_stub_properties("New Suggested Project", projects).get(PROJECT_STATUS_PROPERTY, {}).get("select", {}).get("name") == PROJECT_STUB_STATUS_VALUE, "new project stub uses inactive status", f"expected {PROJECT_STUB_STATUS_VALUE}"),
    ]

    passed = 0
    failed = 0
    for ok, label, detail in checks:
        if print_test_result(ok, label, "" if ok else detail):
            passed += 1
        else:
            failed += 1

    print(f"\nProject relation write-back results: {passed} passed, {failed} failed")
    return failed == 0



print(
    "[PROJECT MODULE LOAD] "
    f"RUN_PROJECT_CANDIDATE_DETECTOR={RUN_PROJECT_CANDIDATE_DETECTOR} "
    f"TEST_MODE={TEST_MODE} "
    f"DRY_RUN={DRY_RUN}"
)



def get_tasks_for_existing_project_discovery():
    """Fetch a broad set of open tasks for one batch emergence pass."""
    limit = max(10, min(globals().get("PROJECT_DISCOVERY_SCAN_LIMIT", 100), 100))
    filter_payload = {
        "and": [
            {"property": "Open Loop", "checkbox": {"equals": True}},
            {"property": "Done", "checkbox": {"equals": False}},
            {"property": "Archived", "checkbox": {"equals": False}},
        ]
    }
    tasks = query_tasks_database(
        filter_payload=filter_payload,
        sorts=[{"timestamp": "last_edited_time", "direction": "descending"}],
        page_size=limit,
    )
    eligible = []
    for task in tasks or []:
        if task_has_project_relation(task) or get_parent_task_id(task):
            continue
        title = get_title(task)
        if not title or title.lower().startswith("clarify next action:"):
            continue
        # Suggested Project is staging metadata, not a reservation. A task is
        # reserved only by an actual Project relation. This means deleting a
        # rejected review project releases its tasks for future discovery.
        eligible.append(task)
    return eligible


def parse_json_object(raw):
    """Parse the first JSON object from an AI response.

    The Responses API normally returns raw JSON when prompted, but models may
    occasionally wrap it in markdown fences or brief surrounding text. This
    helper is deliberately shared by project-emergence callers so JSON parsing
    cannot depend on a local helper defined in another detector path.
    """
    import json

    text = str(raw or "").strip()
    if not text:
        raise ValueError("AI returned an empty response")

    # Strip a simple fenced-code wrapper when present.
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text).strip()

    # Fast path: entire response is JSON.
    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass

    # Fallback: find the first balanced JSON object rather than using a greedy
    # regex, which can overrun if the response contains extra braces.
    start = text.find("{")
    if start < 0:
        raise ValueError(f"AI returned no JSON object: {text[:200]}")

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        ch = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                value = json.loads(text[start:index + 1])
                if not isinstance(value, dict):
                    raise ValueError("AI JSON response was not an object")
                return value

    raise ValueError(f"AI returned an unterminated JSON object: {text[:200]}")


def ask_ai_existing_project_clusters(tasks):
    """Partition existing unprojected tasks into zero or more outcome projects."""
    if len(tasks or []) < 2:
        return []

    keyed = []
    task_by_key = {}
    for i, task in enumerate(tasks, start=1):
        key = f"T{i:03d}"
        keyed.append(f"{key} | {get_title(task)}")
        task_by_key[key] = task

    task_lines = "\n".join(keyed)
    prompt = f"""Find emerging projects among the existing open tasks below.

Return ONLY raw JSON with this shape:
{{
  "projects": [
    {{
      "project_name": "...",
      "confidence": 0.0,
      "reason": "...",
      "finished_outcome": "...",
      "outcome_unfinished": true,
      "member_keys": ["T001", "T002"]
    }}
  ]
}}

Rules:
- A project is a set of 2 or more tasks that work toward one concrete, FINITE, UNFINISHED outcome, deliverable, commitment, or coordinated change.
- You must be able to state what "Done" looks like. If there is no recognizable completion point, do not propose a project.
- The outcome must still be unfinished. Do not reconstruct projects whose outcome is already complete.
- Projects may be finite and small. Do NOT require an ongoing or durable area of responsibility.
- Ongoing areas, maintenance themes, research topics, or collections of similar chores are NOT projects unless the listed tasks clearly converge on a finite outcome.
- Semantic relationship matters more than shared words.
- Shared topic/location alone is not enough. Look for a common outcome, workflow, or dependency.
- Partition selectively: some related-looking tasks may belong; others may not.
- You may return zero, one, or multiple projects.
- Do not force every task into a project.
- A task may belong to at most one proposed project in this pass.
- Prefer specific natural project names such as "Pantry Shelving" rather than vague names such as "Pantry".
- Do not invent tasks or facts. member_keys must come only from the list.
- Strong example: Measure pantry for shelves + Buy shelves for pantry + Install shelves in pantry => Pantry Shelving.
- Weak example: Clean pantry + Replace pantry light bulb + Check expiry dates => usually separate tasks unless there is clear evidence of one coordinated outcome.

Tasks:
{task_lines}
"""
    try:
        response = client.responses.create(model="gpt-4.1-mini", input=prompt)
        raw = getattr(response, "output_text", "") or ""
        data = parse_json_object(raw)
        projects = data.get("projects") or [] if isinstance(data, dict) else []
    except Exception as exc:
        message = str(exc)
        print(f"Existing-task project discovery AI error: {message}")
        if "insufficient_quota" in message or "no credits remaining" in message.lower():
            print("[PROJECT EMERGENCE] BLOCKED: OpenAI API credit balance is exhausted. Semantic discovery cannot run until API credits are available.")
        return []

    accepted = []
    used_keys = set()
    for item in projects:
        if not isinstance(item, dict):
            continue
        name = str(item.get("project_name") or "").strip()
        try:
            confidence = float(item.get("confidence") or 0.0)
        except (TypeError, ValueError):
            confidence = 0.0
        finished_outcome = str(item.get("finished_outcome") or "").strip()
        outcome_unfinished = item.get("outcome_unfinished") is True
        keys = []
        for key in item.get("member_keys") or []:
            if key in task_by_key and key not in used_keys and key not in keys:
                keys.append(key)
        if (
            not name
            or confidence < globals().get("PROJECT_DISCOVERY_MIN_CONFIDENCE", 0.70)
            or len(keys) < 2
            or not finished_outcome
            or not outcome_unfinished
        ):
            continue
        used_keys.update(keys)
        accepted.append({
            "project_name": name,
            "confidence": confidence,
            "reason": str(item.get("reason") or "").strip(),
            "finished_outcome": finished_outcome,
            "outcome_unfinished": outcome_unfinished,
            "tasks": [task_by_key[key] for key in keys],
        })
    return accepted


def count_outstanding_project_reviews(all_projects):
    """Count inactive projects that currently reserve open tasks for emergence review.

    We identify review projects conservatively: an open task must have both a
    Project relation to an inactive project and a Suggested Project value that
    matches that project's current name. Ordinary Someday projects therefore do
    not consume the emergence review budget.
    """
    inactive_by_id = {
        p.get("id"): p for p in (all_projects or [])
        if p.get("id") and not is_active_project(p)
    }
    if not inactive_by_id:
        return 0

    filter_payload = {
        "and": [
            {"property": "Open Loop", "checkbox": {"equals": True}},
            {"property": "Done", "checkbox": {"equals": False}},
            {"property": "Archived", "checkbox": {"equals": False}},
        ]
    }
    tasks = query_tasks_database(filter_payload=filter_payload, page_size=100)
    review_ids = set()
    for task in tasks or []:
        suggested = get_rich_text_plain_value(task.get("properties", {}), SUGGESTED_PROJECT_PROPERTY)
        if not suggested:
            continue
        relations = ((task.get("properties", {}) or {}).get(TASK_PROJECT_RELATION_PROPERTY, {}) or {}).get("relation") or []
        for rel in relations:
            project = inactive_by_id.get(rel.get("id"))
            if project and normalize(get_title(project)) == normalize(suggested):
                review_ids.add(project.get("id"))
    return len(review_ids)


def run_existing_task_project_discovery(all_projects, active_projects):
    """Run one review-only batch discovery pass over existing unprojected tasks."""
    if not globals().get("RUN_EXISTING_TASK_PROJECT_DISCOVERY", True):
        return []

    outstanding = count_outstanding_project_reviews(all_projects)
    max_reviews = max(1, globals().get("PROJECT_DISCOVERY_MAX_REVIEW_PROJECTS", 5))
    if outstanding >= max_reviews:
        print(
            f"[PROJECT EMERGENCE] Review queue full: {outstanding}/{max_reviews} "
            "unreviewed emerging projects. Discovery paused until projects are activated or deleted."
        )
        return []

    slots = max_reviews - outstanding
    tasks = get_tasks_for_existing_project_discovery()
    print(f"[PROJECT EMERGENCE] Existing unprojected tasks eligible: {len(tasks)}")
    if len(tasks) < 2:
        return []

    clusters = ask_ai_existing_project_clusters(tasks)
    if not clusters:
        print("[PROJECT EMERGENCE] No review-worthy existing-task clusters found.")
        return []

    results = []
    max_new = max(1, globals().get("PROJECT_DISCOVERY_MAX_NEW_PER_RUN", 5))
    clusters = clusters[:min(slots, max_new)]
    print(f"[PROJECT EMERGENCE] Review capacity: {outstanding}/{max_reviews}; creating at most {len(clusters)} candidate(s) this run.")
    for cluster in clusters:
        name = cluster["project_name"]
        existing = find_project_by_name(name, all_projects)
        active = existing if existing and is_active_project(existing) else None
        review = existing if existing and not is_active_project(existing) else None
        if existing is None:
            review = create_inactive_project_stub_if_missing(
                name,
                existing_projects=all_projects,
                source_reason=f"Existing-task project emergence: {cluster.get('reason', '')}",
            )
            if review:
                all_projects.append(review)

        print(f"[PROJECT EMERGENCE] Suggested: {name} ({cluster['confidence']:.2f})")
        print(f"  Finished outcome: {cluster.get('finished_outcome')}")
        for task in cluster["tasks"]:
            title = get_title(task)
            update_suggested_project_if_needed(task, name, source="Project Emergence")
            if active:
                set_project_relation_if_safe(task, active, name, 1.0, "Existing-task project emergence matched an active project exactly.")
            elif review:
                set_review_project_relation_if_empty(task, review, name)
            print(f"  - {title}")

        increment_summary("project_candidates_detected")
        results.append(cluster)
    return results


def set_suggested_project_canonical(task, project_name):
    """Synchronize Suggested Project to the canonical related Project name.

    Once AIOS establishes a real Project relation, the relation is authoritative.
    This helper intentionally replaces stale staging text rather than preserving
    a competing historical suggestion.
    """
    project_name = str(project_name or "").strip()
    if not task or not project_name or task.get("dry_run"):
        return False

    props = task.get("properties", {}) or {}
    current = get_rich_text_plain_value(props, SUGGESTED_PROJECT_PROPERTY)
    if current == project_name:
        return False
    if TEST_MODE or DRY_RUN:
        print(f"[DRY RUN] Would sync Suggested Project: {get_title(task)} → {project_name}")
        return False

    response = requests.patch(
        f"https://api.notion.com/v1/pages/{task['id']}",
        headers=headers,
        json={"properties": {SUGGESTED_PROJECT_PROPERTY: _notion_rich_text(project_name)}},
        timeout=30,
    )
    if response.ok:
        increment_summary("suggested_project_updates")
        print(f"Synced Suggested Project to canonical relation: {get_title(task)} → {project_name}")
        # Keep the local object coherent for later passes in the same run.
        props[SUGGESTED_PROJECT_PROPERTY] = _notion_rich_text(project_name)
        return True

    increment_summary("errors")
    print("ERROR syncing Suggested Project:", get_title(task))
    print(response.status_code, response.text)
    return False


def _mark_local_project_relation(task, project):
    """Keep an in-memory task coherent after a successful Project relation write."""
    if not task or not project:
        return
    props = task.setdefault("properties", {})
    props[TASK_PROJECT_RELATION_PROPERTY] = {
        "type": "relation",
        "relation": [{"id": project.get("id")}],
    }


def build_incremental_project_contexts(all_projects, open_tasks):
    """Build active/review project contexts using names plus current member tasks.

    Active projects are always eligible. Inactive projects are eligible only
    when at least one open task is already related to them; this treats emerged
    review projects as candidates without reopening every unrelated Someday row.
    """
    projects_by_id = {
        project.get("id"): project for project in (all_projects or [])
        if project.get("id") and get_title(project)
    }
    members = {project_id: [] for project_id in projects_by_id}

    for task in open_tasks or []:
        title = get_title(task)
        if not title:
            continue
        for project_id in get_relation_ids(task.get("properties", {}), TASK_PROJECT_RELATION_PROPERTY):
            if project_id in members:
                members[project_id].append(title)

    contexts = []
    for project_id, project in projects_by_id.items():
        member_titles = members.get(project_id) or []
        active = is_active_project(project)
        if not active and not member_titles:
            continue
        contexts.append({
            "project": project,
            "project_name": get_title(project),
            "active": active,
            "member_titles": member_titles[:20],
        })
    return contexts


def ask_ai_incremental_project_affinity(tasks, project_contexts):
    """Match newly created untagged tasks to existing active/review projects."""
    tasks = [task for task in (tasks or []) if task and not task_has_project_relation(task)]
    if not tasks or not project_contexts:
        return []

    task_by_key = {}
    task_lines = []
    for i, task in enumerate(tasks, start=1):
        key = f"T{i:03d}"
        task_by_key[key] = task
        task_lines.append(f"{key} | {get_title(task)}")

    project_by_key = {}
    project_lines = []
    for i, context in enumerate(project_contexts, start=1):
        key = f"P{i:03d}"
        project_by_key[key] = context
        members = "; ".join(context.get("member_titles") or []) or "(no current open members)"
        state = "ACTIVE" if context.get("active") else "REVIEW"
        project_lines.append(
            f"{key} | {state} | {context['project_name']} | current tasks: {members}"
        )

    prompt = f"""Match NEW tasks to EXISTING projects when the fit is strong.

Return ONLY raw JSON:
{{
  "matches": [
    {{
      "task_key": "T001",
      "project_key": "P001",
      "confidence": 0.0,
      "reason": "..."
    }}
  ]
}}

Rules:
- Existing projects have priority over inventing a new project.
- Evaluate the project's actual meaning using BOTH its name and its current member tasks.
- A new task should match when it contributes to the same finite outcome, deliverable, or coordinated body of work.
- Shared words or broad topic similarity alone are not enough.
- A task may match at most one project.
- Omit uncertain matches. Do not force every task into a project.
- Review-stage projects are legitimate destinations: adding the relation means "proposed member for review", not automatic activation.
- Prefer a specific project whose current member tasks establish the same intent.
- Example: a new task about refilling Red Fife flour can belong to an existing flour-stock management project when its members are about flour inventory/refilling/usage.

NEW TASKS:
{chr(10).join(task_lines)}

EXISTING PROJECTS:
{chr(10).join(project_lines)}
"""
    try:
        response = client.responses.create(model="gpt-4.1-mini", input=prompt)
        data = parse_json_object(getattr(response, "output_text", "") or "")
    except Exception as exc:
        print(f"[PROJECT AFFINITY] AI error: {exc}")
        return []

    accepted = []
    used_tasks = set()
    threshold = globals().get("PROJECT_INCREMENTAL_AFFINITY_MIN_CONFIDENCE", 0.82)
    for item in (data.get("matches") or []):
        if not isinstance(item, dict):
            continue
        task_key = item.get("task_key")
        project_key = item.get("project_key")
        if task_key in used_tasks or task_key not in task_by_key or project_key not in project_by_key:
            continue
        try:
            confidence = float(item.get("confidence") or 0.0)
        except (TypeError, ValueError):
            confidence = 0.0
        if confidence < threshold:
            continue
        used_tasks.add(task_key)
        accepted.append({
            "task": task_by_key[task_key],
            "context": project_by_key[project_key],
            "confidence": confidence,
            "reason": str(item.get("reason") or "").strip(),
        })
    return accepted


def run_incremental_project_affinity(source_tasks, all_projects, active_projects, open_tasks):
    """Attach newly created tasks to an existing project before new emergence."""
    if not globals().get("RUN_PROJECT_INCREMENTAL_AFFINITY", True):
        return set()

    candidates = [
        task for task in (source_tasks or [])
        if not str(task.get("_manual_project_hint") or "").strip()
        and not task_has_project_relation(task)
    ]
    if not candidates:
        return set()

    contexts = build_incremental_project_contexts(all_projects, open_tasks)
    print(
        f"[PROJECT AFFINITY] Checking {len(candidates)} new task(s) against "
        f"{len(contexts)} active/review project(s)."
    )
    matches = ask_ai_incremental_project_affinity(candidates, contexts)
    matched_ids = set()

    for match in matches:
        task = match["task"]
        context = match["context"]
        project = context["project"]
        project_name = context["project_name"]
        confidence = match["confidence"]
        reason = match["reason"]

        print(
            f"[PROJECT AFFINITY] Match: {get_title(task)} → {project_name} "
            f"({confidence:.2f})"
        )
        relation_set = False
        if context["active"]:
            relation_set = set_project_relation_if_safe(
                task, project, project_name, confidence,
                f"Incremental project affinity. {reason}"
            )
        else:
            relation_set = set_review_project_relation_if_empty(
                task, project, project_name
            )

        if relation_set:
            _mark_local_project_relation(task, project)
            set_suggested_project_canonical(task, project_name)
            matched_ids.add(task.get("id"))

    if matches and not matched_ids:
        print("[PROJECT AFFINITY] Matches were proposed but no relations were written.")
    elif not matches:
        print("[PROJECT AFFINITY] No strong existing-project matches for new tasks.")

    return matched_ids


def run_project_candidate_detector():
    """Detect likely project groupings for tasks created in this run.

    V1 remains conservative:
    - Suggested Project is written to tasks for review
    - missing suggested projects can be created as inactive project stubs
    - Project relation is set only for one unambiguous active project match
    - candidates are printed and optionally logged to the AI Processing Log
    """
    runtime_detector_flag = globals().get(
        'RUN_PROJECT_CANDIDATE_DETECTOR',
        True,
    )

    print(
        "[PROJECT DETECTOR RUNTIME FLAGS] "
        f"TEST_MODE={TEST_MODE} "
        f"DRY_RUN={DRY_RUN} "
        f"RUN_PROJECT_CANDIDATE_DETECTOR={runtime_detector_flag}"
    )

    if TEST_MODE or DRY_RUN or not runtime_detector_flag:

        print(
            "[PROJECT DETECTOR SKIPPED] "
            f"TEST_MODE={TEST_MODE} "
            f"DRY_RUN={DRY_RUN} "
            f"RUN_PROJECT_CANDIDATE_DETECTOR={runtime_detector_flag}"
        )

        return []

    source_tasks = get_project_candidate_source_tasks()
    open_tasks = get_open_tasks_for_project_candidate_scan()

    # M1.3: retroactive discovery is a separate batch partition pass. The legacy
    # seed detector remains available for newly created tasks only.
    operational_context_tasks = (
        build_operational_context_task_set(
            open_tasks
        )
    )


    print("\n--- Project candidate detector ---")

    log_topology_telemetry_event(
        event_type="telemetry_runtime_test",
        seed_task="Telemetry Runtime Validation",
        notes="B2 telemetry pipeline test event",
    )
    print(f"Reviewing {len(source_tasks)} newly created top-level task(s).")
    print(
        "Project relation write-back:",
        "enabled" if RUN_PROJECT_RELATION_WRITEBACK else "disabled",
        f"(RUN_PROJECT_RELATION_WRITEBACK={PROJECT_RELATION_WRITEBACK_RAW!r})",
    )

    if RUN_PROJECT_RELATION_WRITEBACK or RUN_PROJECT_STUB_CREATION:
        all_projects = get_all_projects()
        active_projects = [project for project in all_projects if is_active_project(project) and get_title(project)]
        print(f"Loaded active projects: {len(active_projects)}/{len(all_projects)}")
    else:
        all_projects = []
        active_projects = []
        print("Project relation write-back and project stub creation are disabled; Suggested Project will still be written.")

    # M1.8: before asking whether a new task implies a NEW project, ask whether
    # it belongs to an existing active or review-stage project.
    affinity_matched_ids = run_incremental_project_affinity(
        source_tasks,
        all_projects,
        active_projects,
        open_tasks,
    )

    operational_memory = build_operational_memory_from_tasks(
        operational_context_tasks
    )

    operational_field_strength_index = (
        build_operational_field_strength_index(
            operational_context_tasks
        )
    )

    latent_operational_memory = build_latent_operational_memory(
        open_tasks
    )

    if not RUN_PROJECT_RELATION_WRITEBACK:
        print("Project relation write-back disabled by RUN_PROJECT_RELATION_WRITEBACK; Suggested Project will still be written.")
    if not RUN_PROJECT_STUB_CREATION:
        print("Project stub creation disabled by RUN_PROJECT_STUB_CREATION.")

    detected = []
    claimed_task_ids = set()

    for seed_task in source_tasks:
        if seed_task.get("id") in claimed_task_ids or seed_task.get("id") in affinity_matched_ids:
            continue
        seed_title = get_title(seed_task)

        print(f"[TRACE] Seed task: {seed_title}")

        manual_project = str(seed_task.get("_manual_project_hint") or "").strip()
        if manual_project:
            print(
                f"[MANUAL PROJECT INTENT] {seed_title} → {manual_project}; "
                "manual naming takes precedence over AI project emergence."
            )
            apply_manual_project_intent(
                seed_task,
                manual_project,
                open_tasks,
                all_projects,
                active_projects,
            )
            for task in source_tasks:
                if normalize(str(task.get("_manual_project_hint") or "")) == normalize(manual_project):
                    claimed_task_ids.add(task.get("id"))
            detected.append({
                "seed_title": seed_title,
                "result": {
                    "should_group": True,
                    "project_name": manual_project,
                    "confidence": 1.0,
                    "reason": "Explicit Brain Dump project hint.",
                    "related_titles": [],
                    "manual_project": True,
                },
            })
            continue

        related_candidates = find_related_task_candidates(seed_task, open_tasks)

        if len(related_candidates) < globals().get('PROJECT_CANDIDATE_MIN_RELATED_TASKS', 1):
            continue

        print(
            f"[TRACE] Final merged candidates: "
            f"{len(related_candidates)}"
        )

        result = ask_ai_project_candidate(
            seed_title,
            related_candidates,
        )

        print(
            f"[TRACE] AI should_group: "
            f"{result.get('should_group')}"
        )

        operational_inference = onr.infer_operational_domain(
            seed_title,
            operational_memory,
        )

        inferred_project = operational_inference.get("project")

        operational_field_strength = (
            calculate_operational_field_strength(
                inferred_project,
                operational_field_strength_index,
            )
        )

        reinforcement_confidence = round(
            (
                operational_inference.get("score", 0.0)
                * operational_field_strength
            ),
            2,
        )

        build_operational_field_observability_snapshot(
            seed_title,
            operational_inference,
            operational_field_strength,
        )

        result["reinforcement_confidence"] = (
            reinforcement_confidence
        )

        reinforcement_candidate = None

        if (
            inferred_project
            and reinforcement_confidence >= 0.10
        ):

            reinforcement_candidate = inferred_project

            print(
                f"[Operational Reinforcement Advisory] "
                f"{seed_title} → {inferred_project} "
                f"(score={operational_inference.get('score', 0.0):.2f})"
            )

            result["reinforcement_candidate"] = (
                reinforcement_candidate
            )

            existing_reason = result.get("reason") or ""

            result["reason"] = (
                existing_reason
                + " Operational reinforcement stored as advisory context."
            ).strip()

        latent_cluster = infer_latent_operational_cluster(
            seed_title,
            latent_operational_memory,
        )

        emergent_project = generate_emergent_operational_domain(
            seed_title,
            related_candidates,
        )

        emergence_allowed, emergence_trust = (
            should_allow_emergent_domain(
                latent_cluster,
                operational_inference,
            )
        )

        if (
            latent_cluster.get("should_emerge")
            and emergent_project
            and emergence_allowed
        ):

            print(
                "[Latent Operational Emerence] "
                f"{seed_title} "
                f"→ {emergent_project}"
            )

            log_topology_telemetry_event(
                event_type="latent_operational_emergence",
                seed_task=seed_title,
                top_candidate=emergent_project,
                cluster_size=len(latent_cluster.get("related_titles", [])),
                notes="Latent operational ontology emerged from unresolved task memory.",
            )

            print(
                "[Latent Cluster Size] "
                f"{len(latent_cluster.get('related_titles', []))}"
            )

            print(
                "[Emergent Domain Trust] "
                f"{emergence_trust:.2f}"
            )

            result["project_name"] = emergent_project

            result["reason"] = (
                "AIOS detected a persistent latent "
                "operational domain emerging across "
                "historical unresolved tasks."
            )

        elif should_emerge_new_operational_domain(
            seed_title,
            operational_inference,
            related_candidates,
        ) and emergent_project:

            print(
                "[Operational Domain Emergence] "
                f"{seed_title} "
                f"→ {emergent_project}"
            )

            log_topology_telemetry_event(
                event_type="operational_domain_emergence",
                seed_task=seed_title,
                top_candidate=emergent_project,
                cluster_size=len(related_candidates),
                notes="Operational domain emerged from repeated execution patterns.",
            )

            result["project_name"] = emergent_project

            result["reason"] = (
                "AIOS detected a new operational "
                "domain emerging from repeated "
                "related execution patterns."
            )

        exploratory_allowed = (
            should_allow_exploratory_candidate(
                seed_title,
                related_candidates,
                latent_cluster,
            )
        )

        if (
            not result.get("should_group")
            and not exploratory_allowed
        ):

            print(
                "[TRACE] Candidate suppressed "
                "before ontology pipeline"
            )

            continue

        elif (
            exploratory_allowed
            and not result.get("should_group")
        ):

            print(
                "[Exploratory Ontology Path Enabled] "
                f"{seed_title}"
            )

            log_topology_telemetry_event(
                event_type="exploratory_ontology_enabled",
                seed_task=seed_title,
                cluster_size=len(related_candidates),
                notes="Exploratory ontology path activated.",
            )

            result["should_group"] = True

            print(
                "[TRACE] Exploratory ontology path activated"
            )


        result = expand_project_candidate_related_titles(result, open_tasks)

        ontology_expansion_titles = build_ontology_expansion_set(
            related_candidates,
            latent_cluster,
            operational_inference,
            open_tasks,
        )

        ontology_expansion_count = len(
            ontology_expansion_titles
        )

        print(
            "[Ontology-Aware Expansion] "
            f"{ontology_expansion_count} operational neighbors"
        )

        effective_expansion_size = max(
            len(result.get("related_titles", [])),
            ontology_expansion_count,
        )

        result["effective_expansion_size"] = (
            effective_expansion_size
        )

        result["ontology_expansion_titles"] = (
            ontology_expansion_titles
        )

        print(
            "[Effective Expansion Size] "
            f"{effective_expansion_size}"
        )

        override_allowed, ontology_confidence = (
            should_override_legacy_validation(
                related_candidates,
                latent_cluster,
                exploratory_allowed,
                operational_inference,
            )
        )

        print(
            "[Ontology Confidence] "
            f"{ontology_confidence:.2f}"
        )

        result["ontology_override_allowed"] = (
            override_allowed
        )

        result["ontology_confidence"] = (
            ontology_confidence
        )


        operational_ontology_detected = any([
            exploratory_allowed,
            latent_cluster.get("should_emerge"),
            ontology_confidence >= 0.55,
            effective_expansion_size >= 5,
        ])

        result["operational_ontology_detected"] = (
            operational_ontology_detected
        )

        print(
            "[Operational Ontology Detected] "
            f"{operational_ontology_detected}"
        )

        reinforcement_candidate = (
            result.get("reinforcement_candidate")
        )

        emergent_project = result.get("project_name")

        if reinforcement_candidate:

            if reinforcement_strengthens_emergent_ontology(
                reinforcement_candidate,
                emergent_project,
            ):

                print(
                    "[Ontology-Compatible Reinforcement] "
                    f"{reinforcement_candidate}"
                )

                if not emergent_project:
                    result["project_name"] = (
                        reinforcement_candidate
                    )

            else:

                b2_log(
                    "[Ontology Reinforcement Rejected] "
                    f"{reinforcement_candidate}"
                )

                log_topology_telemetry_event(
                    event_type="reinforcement_rejected",
                    seed_task=seed_title,
                    top_candidate=reinforcement_candidate,
                    suppressed=True,
                    notes="Reinforcement candidate rejected by ontology compatibility filter.",
                )

        seed_specificity = (
            calculate_operational_specificity(
                seed_title
            )
        )

        print(
            "[Operational Specificity] "
            f"{seed_title} -> {seed_specificity}"
        )

        if seed_specificity >= 6:

            print(
                "[High Infrastructure Specificity] "
                f"{seed_title}"
            )

            log_topology_telemetry_event(
                event_type="high_specificity_detected",
                seed_task=seed_title,
                specificity=seed_specificity,
                notes="High operational specificity detected.",
            )

        is_valid_candidate, validation_reason = validate_project_candidate(seed_title, result)

        if is_valid_candidate:

            print(
                "[ONTOLOGY CANDIDATE ACCEPTED] "
                f"{result.get('project_name')}"
            )
        if not is_valid_candidate:
            print("Project candidate suppressed:", seed_title, "→", validation_reason)
            continue

        print(
            "[ONTOLOGY CRYSTALLIZATION SUCCESS] "
            f"{result.get('project_name')}"
        )

        log_topology_telemetry_event(
            event_type="ontology_crystallized",
            seed_task=seed_title,
            top_candidate=result.get("project_name"),
            cluster_size=effective_expansion_size,
            specificity=seed_specificity,
            notes="Operational ontology crystallized successfully.",
        )

        print(
            "[Ontology Expansion Titles] "
            f"{result.get('ontology_expansion_titles', [])[:10]}"
        )

        print(
            "[ONTOLOGY CRYSTALLIZATION PROMOTED] "
            f"{result.get('project_name')}"
        )

        print(
            "[Governance State] "
            "Operational ontology granted primary authority."
        )

        print(
            "[ONTOLOGY GOVERNANCE SUCCESS] "
            f"{result.get('project_name')}"
        )

        print(
            "[Ontology Confidence Final] "
            f"{result.get('ontology_confidence')}"
        )

        print_project_candidate(seed_title, result)
        log_project_candidate(seed_title, result)
        apply_project_candidate_writeback(seed_task, result, open_tasks, all_projects, active_projects)

        # Do not emit the same cluster repeatedly from each member during one run.
        selected_titles = {seed_title}
        selected_titles.update(result.get("related_titles") or [])
        selected_titles.update(
            item.get("title") for item in (result.get("expanded_related_titles") or [])
            if item.get("title")
        )
        for task in [seed_task] + list(open_tasks or []):
            if get_title(task) in selected_titles:
                claimed_task_ids.add(task.get("id"))

        increment_summary("project_candidates_detected")
        detected.append({
            "seed_title": seed_title,
            "result": result,
        })

    emergence_results = run_existing_task_project_discovery(all_projects, active_projects)
    if emergence_results:
        detected.extend({"seed_title": "Existing Task Batch", "result": item} for item in emergence_results)

    if not detected:
        print("Project candidate detector: no review-worthy candidates found.")

    return detected




# ============================================================
# PROJECT CANONICALIZATION DIAGNOSTICS
# ============================================================

def log_project_similarity_diagnostics(
    candidate,
    existing_projects,
):

    if not candidate:
        return

    diagnostics = []

    for existing in existing_projects:

        score = project_similarity_score(
            candidate,
            existing,
        )

        diagnostics.append(
            (existing, score)
        )

    diagnostics.sort(
        key=lambda x: x[1],
        reverse=True,
    )

    print("\n[Project Canonicalization Diagnostics]")
    print(f"candidate='{candidate}'")

    for existing, score in diagnostics[:5]:

        print(
            f"  similarity={score:.2f} "
            f"project='{existing}'"
        )

