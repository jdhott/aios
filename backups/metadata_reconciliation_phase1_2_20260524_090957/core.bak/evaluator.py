"""
AIOS Central Evaluation Engine — Ranking Component Diagnostics
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


COMMON_ACTION_VERBS = {
    "buy", "call", "check", "clean", "confirm", "create",
    "email", "finish", "fix", "follow", "get", "install",
    "make", "move", "order", "organize", "pay", "plan",
    "prepare", "purchase", "reply", "review", "schedule",
    "send", "set", "submit", "update", "write",
}

VAGUE_TERMS = {
    "thing",
    "stuff",
    "something",
    "someone",
}

OPERATIONAL_KEYWORDS = {
    "menu",
    "bakery",
    "school",
    "bread",
    "bake",
    "inventory",
    "packaging",
    "production",
    "pool",
    "garden",
}

STRATEGIC_KEYWORDS = {
    "architecture",
    "review",
    "system",
    "plan",
    "strategy",
    "improve",
    "develop",
}


@dataclass
class RankingComponent:
    name: str
    score: int


@dataclass
class TaskEvaluation:
    is_jdi: bool = False
    is_quick_win: bool = False

    needs_clarification: bool = False
    clarification_reasons: List[str] = field(default_factory=list)

    should_break_down: bool = False
    breakdown_reasons: List[str] = field(default_factory=list)

    rewrite_type: Optional[str] = None
    rewrite_reasons: List[str] = field(default_factory=list)

    ranking_score: int = 0
    ranking_reasons: List[str] = field(default_factory=list)
    ranking_components: List[RankingComponent] = field(default_factory=list)

    is_execution_eligible: bool = False
    rejection_reasons: List[str] = field(default_factory=list)


def _title(task: Dict) -> str:
    return (task.get("Task Name") or "").strip()


def _lower(task: Dict) -> str:
    return _title(task).lower()


def is_jdi_task(task: Dict) -> bool:

    if task.get("Just Do It") is True:
        return True

    title = _lower(task)

    return (
        " jdi" in title
        or "just do it" in title
    )


def is_quick_win(task: Dict) -> bool:

    duration = task.get("Duration")

    return duration in [
        "5 min",
        "10 min",
        "15 min",
    ]


def evaluate_clarification(task: Dict):

    reasons = []

    title = _title(task)
    lower = _lower(task)

    if not title:
        reasons.append("empty_title")

    if len(title.split()) <= 1:
        reasons.append("single_word")

    if lower in VAGUE_TERMS:
        reasons.append("vague_term")

    if title and len(title.split()) >= 3:
        reasons = [
            r for r in reasons
            if r != "single_word"
        ]

    has_action_verb = any(
        lower.startswith(f"{verb} ")
        for verb in COMMON_ACTION_VERBS
    )

    # Previously, any task lacking a leading action verb
    # automatically triggered clarification.
    #
    # This proved too aggressive for many legitimate
    # human-executable tasks such as:
    # - "Check airline prices for Italy trip"
    # - "Organize papers in my office"
    # - "Buy shampoo bars"
    #
    # Only trigger clarification for structurally weak
    # or fragmentary titles.

    structurally_weak = len(title.split()) < 3

    if not has_action_verb and structurally_weak:
        reasons.append("missing_action_verb")

    needs_clarification = len(reasons) > 0

    return needs_clarification, reasons


def evaluate_rewrite(task: Dict):

    reasons = []

    title = _title(task)

    if not title:
        return None, reasons

    normalized = " ".join(title.split())

    if normalized != title:
        reasons.append("whitespace_cleanup")

    if title and title[0].islower():
        reasons.append("capitalization")

    if "  " in title:
        reasons.append("double_space")

    if not reasons:
        return None, reasons

    return "soft", reasons


# ============================================================
# RANKING COMPONENT HELPERS
# ============================================================

def score_priority(priority) -> Tuple[int, Optional[str]]:

    if priority == "High Priority":
        return 25, "high_priority"

    return 0, None


def score_urgency(urgency) -> Tuple[int, Optional[str]]:

    if urgency == "High Urgency":
        return 25, "high_urgency"

    if urgency == "Medium Urgency":
        return 10, "medium_urgency"

    return 0, None


def score_quick_win(duration) -> Tuple[int, Optional[str]]:

    if duration in [
        "5 min",
        "10 min",
        "15 min",
    ]:
        return 3, "quick_win"

    return 0, None


def score_effort(effort) -> Tuple[int, Optional[str]]:

    if effort == "Medium Effort":
        return 3, "medium_effort"

    if effort == "Large Effort":
        return 7, "large_effort"

    return 0, None


def score_operational_context(title) -> Tuple[int, Optional[str]]:

    if any(
        keyword in title
        for keyword in OPERATIONAL_KEYWORDS
    ):
        return 5, "operational_context"

    return 0, None


def score_strategic_context(title) -> Tuple[int, Optional[str]]:

    if any(
        keyword in title
        for keyword in STRATEGIC_KEYWORDS
    ):
        return 4, "strategic_context"

    return 0, None


def score_planning_work(title) -> Tuple[int, Optional[str]]:

    if title.startswith("plan "):
        return 4, "planning_work"

    return 0, None


def score_preparation_work(title) -> Tuple[int, Optional[str]]:

    if title.startswith("prepare "):
        return 4, "preparation_work"

    return 0, None


def evaluate_ranking(task: Dict):

    total_score = 0
    reasons = []
    components = []

    title = _lower(task)

    priority = task.get("Priority")
    urgency = task.get("Urgency")
    duration = task.get("Duration")
    effort = task.get("Effort")

    scoring_functions = [
        lambda: score_priority(priority),
        lambda: score_urgency(urgency),
        lambda: score_quick_win(duration),
        lambda: score_effort(effort),
        lambda: score_operational_context(title),
        lambda: score_strategic_context(title),
        lambda: score_planning_work(title),
        lambda: score_preparation_work(title),
    ]

    for fn in scoring_functions:

        score, reason = fn()

        if score > 0 and reason:

            total_score += score
            reasons.append(reason)

            components.append(
                RankingComponent(
                    name=reason,
                    score=score,
                )
            )

    return total_score, reasons, components


def is_reasonably_actionable(task: Dict) -> bool:

    lower = _lower(task)

    if not lower:
        return False

    return any(
        lower.startswith(f"{verb} ")
        for verb in COMMON_ACTION_VERBS
    )


def evaluate_breakdown(task: Dict):

    reasons = []

    if is_jdi_task(task):
        reasons.append("jdi")

    if is_quick_win(task):
        reasons.append("quick_win")

    clarification_needed, _ = evaluate_clarification(task)

    if clarification_needed:
        reasons.append("needs_clarification")

    effort = task.get("Effort")

    if effort in [
        "Large Effort",
        "Very Large Effort",
    ]:
        reasons.append("large_effort")

    should_break_down = (
        "large_effort" in reasons
        and "jdi" not in reasons
        and "quick_win" not in reasons
        and "needs_clarification" not in reasons
    )

    return should_break_down, reasons


def evaluate_execution_eligibility(task: Dict):

    reasons = []

    if task.get("Deferred"):
        reasons.append("deferred")

    if is_jdi_task(task):
        reasons.append("jdi")

    if is_quick_win(task):
        reasons.append("quick_win")

    clarification_needed, _ = evaluate_clarification(task)

    if clarification_needed:
        reasons.append("needs_clarification")

    if not is_reasonably_actionable(task):
        reasons.append("non_actionable")

    return len(reasons) == 0, reasons


def evaluate_task(task: Dict) -> TaskEvaluation:

    evaluation = TaskEvaluation()

    evaluation.is_jdi = is_jdi_task(task)
    evaluation.is_quick_win = is_quick_win(task)

    (
        evaluation.needs_clarification,
        evaluation.clarification_reasons,
    ) = evaluate_clarification(task)

    (
        evaluation.should_break_down,
        evaluation.breakdown_reasons,
    ) = evaluate_breakdown(task)

    (
        evaluation.rewrite_type,
        evaluation.rewrite_reasons,
    ) = evaluate_rewrite(task)

    (
        evaluation.ranking_score,
        evaluation.ranking_reasons,
        evaluation.ranking_components,
    ) = evaluate_ranking(task)

    (
        evaluation.is_execution_eligible,
        evaluation.rejection_reasons,
    ) = evaluate_execution_eligibility(task)

    return evaluation