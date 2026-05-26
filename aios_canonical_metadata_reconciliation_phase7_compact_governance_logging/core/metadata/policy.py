"""
AIOS Canonical Metadata Policy Registry — Phase 1

This module is intentionally declarative. It does not read, score, rank, or
mutate Notion pages. It centralizes the ownership doctrine used by reconciliation
so future metadata cleanup can expand without reintroducing distributed authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple, List

VERSION = "canonical-metadata-policy-v0.4.1"


@dataclass(frozen=True)
class MetadataFieldPolicy:
    canonical_name: str
    aliases: Tuple[str, ...]
    owner: str
    role: str
    mutation_policy: str
    reconciliation_policy: str


EXECUTION_SCORE = MetadataFieldPolicy(
    canonical_name="Execution Score",
    aliases=("Execution Score", "Score"),
    owner="canonical_execution_authority",
    role="canonical_execution_state",
    mutation_policy="execution_engine_may_write; reconciliation_may_clear_when_stale",
    reconciliation_policy="clear_on_closed_done; clear_on_deferred_future; clear_on_jdi",
)

EXECUTION_RANK = MetadataFieldPolicy(
    canonical_name="Execution Rank",
    aliases=("Execution Rank", "Rank"),
    owner="canonical_execution_authority",
    role="canonical_execution_state",
    mutation_policy="execution_engine_may_write; reconciliation_may_rewrite_canonically",
    reconciliation_policy="canonicalize_active_rank_sequence; clear_on_closed_done; clear_on_deferred_future; clear_on_jdi",
)

BEST_NEXT_ACTION = MetadataFieldPolicy(
    canonical_name="Best Next Action",
    aliases=("Best Next Action", "Best Next", "BNA"),
    owner="canonical_execution_authority",
    role="canonical_execution_surface",
    mutation_policy="execution_engine_only",
    reconciliation_policy="diagnose_missing_rank_or_score; clear_on_closed_done; clear_on_deferred_future; clear_on_jdi",
)

QUICK_WIN = MetadataFieldPolicy(
    canonical_name="Quick Win",
    aliases=("Quick Win", "Quick Wins", "QuickWin"),
    owner="quick_win_overlay",
    role="derived_presentation_overlay",
    mutation_policy="quick_win_lane_may_write; reconciliation_may_clear_when_stale",
    reconciliation_policy="clear_on_closed_done; clear_on_deferred_future; clear_on_jdi",
)

DO_TODAY = MetadataFieldPolicy(
    canonical_name="Do = Today",
    aliases=("Do = Today", "Do Today", "Today"),
    owner="user_manual_pin",
    role="manual_user_metadata",
    mutation_policy="manual_only",
    reconciliation_policy="ignored_by_execution_reconciliation",
)

FOCUS_NOW = MetadataFieldPolicy(
    canonical_name="Focus Now",
    aliases=("Focus Now", "Focus"),
    owner="deprecated_legacy_metadata",
    role="deprecated",
    mutation_policy="no_runtime_mutation",
    reconciliation_policy="ignored_by_execution_reconciliation",
)

STRONG_CANDIDATE = MetadataFieldPolicy(
    canonical_name="Strong Candidate",
    aliases=("Strong Candidate", "Strong Next Move", "Strong Candidate?"),
    owner="deprecated_legacy_metadata",
    role="deprecated",
    mutation_policy="no_runtime_mutation",
    reconciliation_policy="ignored_by_execution_reconciliation",
)

JDI = MetadataFieldPolicy(
    canonical_name="JDI",
    aliases=("JDI", "Just Do It", "Just Do It?", "Just Do It"),
    owner="execution_eligibility_guard",
    role="exclusion_signal",
    mutation_policy="not_owned_by_reconciliation",
    reconciliation_policy="execution_state_must_not_be_persisted",
)

DEFER_UNTIL = MetadataFieldPolicy(
    canonical_name="Defer Until",
    aliases=("Defer Until", "Deferred Until", "Defer"),
    owner="temporal_authority",
    role="temporal_exclusion_signal",
    mutation_policy="not_owned_by_execution_reconciliation",
    reconciliation_policy="future_deferred_tasks_must_not_carry_execution_state",
)

DONE = MetadataFieldPolicy(
    canonical_name="Done",
    aliases=("Done", "Complete", "Completed"),
    owner="task_lifecycle",
    role="closure_signal",
    mutation_policy="not_owned_by_reconciliation",
    reconciliation_policy="closed_done_tasks_must_not_carry_execution_state",
)

OPEN_LOOP = MetadataFieldPolicy(
    canonical_name="Open Loop",
    aliases=("Open Loop", "Open", "Active"),
    owner="task_lifecycle",
    role="open_state_signal",
    mutation_policy="not_owned_by_reconciliation",
    reconciliation_policy="closed_done_tasks_must_not_carry_execution_state",
)

TASK_TITLE = MetadataFieldPolicy(
    canonical_name="Task Name",
    aliases=("Task Name", "Name", "Title", "Task"),
    owner="task_identity",
    role="identity",
    mutation_policy="not_owned_by_reconciliation",
    reconciliation_policy="read_only_identifier",
)

PARENT_TASK = MetadataFieldPolicy(
    canonical_name="Parent Task",
    aliases=("Parent Task", "Parent", "Sub-item", "Sub Item"),
    owner="task_structure",
    role="hierarchy_signal",
    mutation_policy="not_owned_by_reconciliation",
    reconciliation_policy="read_only_diagnostic_flag",
)

CANONICAL_EXECUTION_FIELDS: Tuple[MetadataFieldPolicy, ...] = (
    EXECUTION_SCORE,
    EXECUTION_RANK,
    BEST_NEXT_ACTION,
)

PRESENTATION_OVERLAY_FIELDS: Tuple[MetadataFieldPolicy, ...] = (
    QUICK_WIN,
)

MANUAL_ONLY_FIELDS: Tuple[MetadataFieldPolicy, ...] = (
    DO_TODAY,
)

DEPRECATED_EXECUTION_FIELDS: Tuple[MetadataFieldPolicy, ...] = (
    FOCUS_NOW,
    STRONG_CANDIDATE,
)

RECONCILIATION_POLICY_FIELDS: Tuple[MetadataFieldPolicy, ...] = (
    EXECUTION_SCORE,
    EXECUTION_RANK,
    BEST_NEXT_ACTION,
    QUICK_WIN,
    DO_TODAY,
    FOCUS_NOW,
    STRONG_CANDIDATE,
    JDI,
    DEFER_UNTIL,
    DONE,
    OPEN_LOOP,
)


def aliases(field: MetadataFieldPolicy) -> Tuple[str, ...]:
    return field.aliases


def policy_status_lines() -> List[str]:
    """Return stable, grep-friendly policy lines for runtime logs."""
    return [
        f"[Metadata Policy] Version: {VERSION}",
        "[Metadata Policy] Canonical execution fields: " + ", ".join(f.canonical_name for f in CANONICAL_EXECUTION_FIELDS),
        "[Metadata Policy] Presentation overlays: " + ", ".join(f.canonical_name for f in PRESENTATION_OVERLAY_FIELDS),
        "[Metadata Policy] Manual-only fields: " + ", ".join(f.canonical_name for f in MANUAL_ONLY_FIELDS),
        "[Metadata Policy] Deprecated execution fields ignored by reconciliation: " + ", ".join(f.canonical_name for f in DEPRECATED_EXECUTION_FIELDS),
    ]
