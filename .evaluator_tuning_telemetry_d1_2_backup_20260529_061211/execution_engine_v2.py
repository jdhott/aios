print("=== EXECUTION ENGINE V2 MODULE LOADED ===")
print("=== EXECUTION AUTHORITY CONSOLIDATION — PHASE 2G: COMBINED QUICK WIN RANKING + QUIET OVERLAY ===")
print("=== FULL EVALUATOR RANKING AUTHORITY ACTIVE ===")

EXECUTION_ENGINE_WINNERS = []

from datetime import datetime, timezone

import os
from dataclasses import dataclass, field


# ============================================================
# EVALUATOR IMPORTS
# ============================================================

EVALUATOR_AVAILABLE = False

try:
    from core.evaluator import evaluate_task

    EVALUATOR_AVAILABLE = True

    print("[Evaluator] Successfully loaded core.evaluator")

except Exception as e:

    print(f"[Evaluator] Import failed: {e}")


@dataclass
class ExecutionScoreResult:
    legacy_score: int
    legacy_reasons: list

    evaluator_score: int = 0
    evaluator_components: list = field(default_factory=list)

    divergence: int = 0


# ============================================================
# EXECUTION SCORING ORCHESTRATION
# ============================================================

def format_ranking_components(components):

    if not components:
        return "[]"

    return "[" + ", ".join(
        f"{c.name}(+{c.score})"
        for c in components
    ) + "]"


def evaluate_execution_scoring(task):

    result = compute_execution_score(task)

    legacy_score = result["score"]
    legacy_reasons = result["reasons"]

    orchestration = ExecutionScoreResult(
        legacy_score=legacy_score,
        legacy_reasons=legacy_reasons,
    )

    if not EVALUATOR_AVAILABLE:
        return orchestration

    try:

        props = task.get("properties", {})

        
        # Evaluator ranking diagnostics active

        evaluation = evaluate_task({
            "Task Name": extract_title(task),

            "Priority": safe_nested_get(
                props,
                "Priority",
                "select",
                "name"
            ),

            "Urgency": safe_nested_get(
                props,
                "Urgency",
                "select",
                "name"
            ),

            "Duration": safe_nested_get(
                props,
                "Duration",
                "select",
                "name"
            ),

            "Effort": safe_nested_get(
                props,
                "Effort",
                "select",
                "name"
            ),

            "Just Do It": safe_nested_get(
                props,
                "Just Do It",
                "checkbox"
            ),
        })

        orchestration.evaluator_score = (
            evaluation.ranking_score
        )

        orchestration.evaluator_components = (
            evaluation.ranking_components
        )

        orchestration.divergence = (
            orchestration.evaluator_score
            - orchestration.legacy_score
        )

        if orchestration.divergence != 0 and _verbose_execution_diagnostics_enabled():

            print(
                "[Ranking Shadow V3] "
                f"title={extract_title(task)} | "
                f"legacy={orchestration.legacy_score} | "
                f"evaluator={orchestration.evaluator_score} | "
                f"divergence={orchestration.divergence} | "
                f"components={format_ranking_components(orchestration.evaluator_components)}"
            )

    except Exception as e:

        if _verbose_execution_diagnostics_enabled():
            print(
                "[Ranking Shadow V3] "
                f"evaluation failed: {e}"
            )

    return orchestration



# ============================================================
# EVALUATOR TUNING TELEMETRY — D1.1
# ============================================================

def _score_band(score):
    """Compact score band used for read-only evaluator tuning telemetry."""
    try:
        score = int(score or 0)
    except Exception:
        score = 0

    if score <= 0:
        return "zero"
    if score <= 3:
        return "low_1_3"
    if score <= 10:
        return "medium_4_10"
    if score <= 25:
        return "high_11_25"
    return "very_high_26_plus"


def _increment(counter, key, amount=1):
    counter[key] = counter.get(key, 0) + amount


def emit_evaluator_tuning_telemetry(ranked, winners):
    """Emit compact, read-only diagnostics for evaluator tuning preparation.

    This function does not mutate tasks, rankings, Notion metadata, project
    cognition, dashboard state, or execution authority. It only summarizes the
    in-memory ranked pool already produced by Execution Engine V2.
    """
    try:
        ranked = ranked or []
        winners = winners or []

        score_bands = {}
        reason_counts = {}
        winner_reason_counts = {}
        source_counts = {
            "evaluator": 0,
            "legacy_fallback": 0,
            "baseline_fallback": 0,
            "zero_signal": 0,
        }

        low_signal_winners = 0

        for item in ranked:
            score = item.get("score", 0)
            reasons = item.get("reasons") or []
            evaluator_score = item.get("evaluator_score", 0) or 0
            legacy_score = item.get("legacy_score", 0) or 0

            _increment(score_bands, _score_band(score))

            if not reasons:
                source_counts["zero_signal"] += 1
            elif reasons == ["baseline_executable"]:
                source_counts["baseline_fallback"] += 1
            elif evaluator_score and score == evaluator_score:
                source_counts["evaluator"] += 1
            elif legacy_score and score == legacy_score:
                source_counts["legacy_fallback"] += 1
            else:
                if evaluator_score:
                    source_counts["evaluator"] += 1
                elif legacy_score:
                    source_counts["legacy_fallback"] += 1
                else:
                    source_counts["zero_signal"] += 1

            for reason in reasons:
                _increment(reason_counts, reason)

        for item in winners:
            reasons = item.get("reasons") or []
            score = item.get("score", 0) or 0

            if score <= 3 or reasons == ["baseline_executable"]:
                low_signal_winners += 1

            for reason in reasons:
                _increment(winner_reason_counts, reason)

        def fmt(counter):
            if not counter:
                return "none"
            return "; ".join(
                f"{key}={counter[key]}"
                for key in sorted(counter)
            )

        print("\\n--- Evaluator Tuning Telemetry D1.1 ---")
        print(
            "[Evaluator Tuning] pool: "
            f"ranked={len(ranked)}; winners={len(winners)}"
        )
        print("[Evaluator Tuning] score_bands: " f"{fmt(score_bands)}")
        print("[Evaluator Tuning] scoring_sources: " f"{fmt(source_counts)}")
        print("[Evaluator Tuning] signal_distribution: " f"{fmt(reason_counts)}")
        print("[Evaluator Tuning] bna_signal_distribution: " f"{fmt(winner_reason_counts)}")
        print("[Evaluator Tuning] low_signal_bna_count: " f"{low_signal_winners}")
        print(
            "[Evaluator Tuning] authority_impact=none; "
            "mutations=0; mode=read_only_observation"
        )

    except Exception as e:
        print(f"[Evaluator Tuning] telemetry failed nonfatally: {e}")


MAX_BEST_NEXT_ACTIONS = 5


def _verbose_execution_diagnostics_enabled():
    """Return True when legacy per-task execution diagnostics should be printed.

    Default runtime logs should stay compact now that the governance telemetry
    summary is canonical. Set AIOS_VERBOSE_EXECUTION_DIAGNOSTICS=true for
    targeted debugging of per-task shadow scoring and baseline fallbacks.
    """
    return str(os.getenv("AIOS_VERBOSE_EXECUTION_DIAGNOSTICS", "")).strip().lower() in {"1", "true", "yes", "on"}


def safe_nested_get(value, *keys):
    current = value

    for key in keys:
        if current is None:
            return None

        if not isinstance(current, dict):
            return None

        current = current.get(key)

    return current




def normalize_property_name(name):
    return "".join(
        ch.lower()
        for ch in str(name or "")
        if ch.isalnum()
    )


def get_property_case_insensitive(props, *candidate_names):
    if not isinstance(props, dict):
        return None

    for name in candidate_names:
        if name in props:
            return props.get(name)

    normalized_candidates = {
        normalize_property_name(name)
        for name in candidate_names
    }

    for actual_name, value in props.items():
        if normalize_property_name(actual_name) in normalized_candidates:
            return value

    return None


def get_checkbox_like_property(props, *candidate_names):
    """Read a Notion checkbox-like property defensively.

    Primary support is for native checkbox properties, but this also handles
    formula booleans and rollup booleans defensively so execution exclusion
    remains stable if the Notion schema/view changes slightly.
    """
    prop = get_property_case_insensitive(props, *candidate_names)

    if not isinstance(prop, dict):
        return False

    if prop.get("checkbox") is True:
        return True

    formula = prop.get("formula")
    if isinstance(formula, dict) and formula.get("boolean") is True:
        return True

    rollup = prop.get("rollup")
    if isinstance(rollup, dict):
        if rollup.get("type") == "array":
            for item in rollup.get("array", []) or []:
                if isinstance(item, dict):
                    if item.get("checkbox") is True:
                        return True
                    item_formula = item.get("formula")
                    if isinstance(item_formula, dict) and item_formula.get("boolean") is True:
                        return True
        if rollup.get("checkbox") is True:
            return True
        if rollup.get("boolean") is True:
            return True

    return False

def extract_title(task):
    props = task.get("properties", {}) or {}

    title_items = safe_nested_get(
        props,
        "Task Name",
        "title"
    ) or []

    if title_items:
        first = title_items[0] or {}
        return first.get("plain_text", "Untitled")

    return "Untitled"


def parse_notion_date(date_string):
    if not date_string:
        return None

    try:
        return datetime.fromisoformat(
            str(date_string).replace("Z", "+00:00")
        ).date()

    except Exception:
        try:
            return datetime.strptime(
                str(date_string)[:10],
                "%Y-%m-%d"
            ).date()

        except Exception:
            return None


def get_defer_until_date(task):
    props = task.get("properties", {}) or {}

    defer_start = safe_nested_get(
        props,
        "Defer Until",
        "date",
        "start"
    )

    return parse_notion_date(defer_start)


def is_deferred_until_future(task, today=None):
    defer_until = get_defer_until_date(task)

    if not defer_until:
        return False

    today = today or datetime.now().date()

    return defer_until > today


def is_jdi(task):
    """Return True for explicit JDI tasks.

    Do is no longer an execution authority. Historical values such as
    Do = JDI are ignored here so the manual Do field cannot exclude, rank,
    or otherwise control Execution Engine V2.

    The canonical authority for JDI exclusion is the native Notion checkbox
    property named exactly "Just Do It". The reader is defensive about
    casing/spacing and checkbox-like booleans so JDI tasks cannot leak back
    into Execution Score / Execution Rank after schema/view changes.
    """
    props = task.get("properties", {}) or {}

    if get_checkbox_like_property(
        props,
        "Just Do It",
        "JDI",
        "JustDoIt",
    ):
        return True

    title = extract_title(task).strip().lower()

    return (
        title == "jdi"
        or title.startswith("jdi ")
        or title.endswith(" jdi")
        or " just do it" in f" {title}"
    )


def is_quick_win(task):
    props = task.get("properties", {}) or {}

    return safe_nested_get(
        props,
        "Quick Win",
        "checkbox"
    ) is True


COMMON_ACTION_VERBS = {
    "buy", "call", "check", "clean", "confirm", "create",
    "email", "finish", "fix", "follow", "get", "install",
    "make", "move", "order", "organize", "pay", "plan",
    "prepare", "purchase", "reply", "review", "schedule",
    "send", "set", "submit", "update", "write",
}


def is_reasonably_actionable(task):
    title = extract_title(task).strip().lower()

    if not title:
        return False

    vague_patterns = {
        "thing",
        "stuff",
        "something",
        "someone",
    }

    if title in vague_patterns:
        return False

    return any(
        title.startswith(f"{verb} ")
        for verb in COMMON_ACTION_VERBS
    )


def compute_execution_score(task):
    props = task.get("properties", {}) or {}

    score = 0
    reasons = []

    priority = safe_nested_get(
        props,
        "Priority",
        "select",
        "name"
    )

    if priority == "High Priority":
        score += 30
        reasons.append("high_priority")

    elif priority == "Medium Priority":
        score += 15
        reasons.append("medium_priority")

    urgency = safe_nested_get(
        props,
        "Urgency",
        "select",
        "name"
    )

    if urgency == "High Urgency":
        score += 25
        reasons.append("high_urgency")

    elif urgency == "Medium Urgency":
        score += 10
        reasons.append("medium_urgency")

    due_date = safe_nested_get(
        props,
        "Due",
        "date",
        "start"
    )

    if due_date:
        try:
            due_dt = datetime.fromisoformat(
                due_date.replace("Z", "+00:00")
            )

            now = datetime.now(timezone.utc)

            days = (due_dt - now).days

            if days <= 0:
                score += 30
                reasons.append("due_today_or_overdue")

            elif days <= 2:
                score += 20
                reasons.append("due_soon")

            elif days <= 7:
                score += 10
                reasons.append("due_this_week")

        except Exception:
            pass

    duration = safe_nested_get(
        props,
        "Duration",
        "select",
        "name"
    )

    if duration in ["5 min", "10 min", "15 min"]:
        score += 3
        reasons.append("quick_win")

    return {
        "score": score,
        "reasons": reasons,
    }


def safe_update_task(update_fn, task_id, properties):
    try:
        update_fn(task_id, properties)
        return True

    except Exception as e:
        print(f"[Execution Engine V2] update failed: {task_id} -> {e}")
        return False


def is_execution_active(task):
    props = task.get("properties", {}) or {}

    score = safe_nested_get(
        props,
        "Execution Score",
        "number"
    )

    rank = safe_nested_get(
        props,
        "Execution Rank",
        "number"
    )

    return (
        (score or 0) > 0
        or rank is not None
    )


def get_execution_active_tasks(open_tasks):
    return [
        task for task in open_tasks
        if is_execution_active(task)
    ]


def filter_execution_eligible_tasks(open_tasks):
    eligible = []

    diagnostics = {
        "total_open_tasks": len(open_tasks),
        "rejected_deferred": 0,
        "rejected_jdi": 0,
        "included_quick_win": 0,
        "rejected_non_actionable": 0,
        "eligible": 0,
    }

    for task in open_tasks:
        if is_deferred_until_future(task):
            diagnostics["rejected_deferred"] += 1
            continue

        if is_jdi(task):
            diagnostics["rejected_jdi"] += 1
            continue

        if is_quick_win(task):
            diagnostics["included_quick_win"] += 1
            # Phase 2G: Quick Wins remain eligible for canonical Execution Rank.
            # They are not rejected before ranking or non-actionable filtering.
            eligible.append(task)
            continue

        if not is_reasonably_actionable(task):
            diagnostics["rejected_non_actionable"] += 1
            continue

        eligible.append(task)

    diagnostics["eligible"] = len(eligible)

    print("\\n--- Execution Eligibility Scan ---")
    print(f"Total open tasks: {diagnostics['total_open_tasks']}")
    print(f"Rejected deferred: {diagnostics['rejected_deferred']}")
    print(f"Rejected JDI: {diagnostics['rejected_jdi']}")
    print(f"Quick Wins included in ranking: {diagnostics['included_quick_win']}")
    print(f"Rejected non-actionable: {diagnostics['rejected_non_actionable']}")
    print(f"Eligible execution tasks: {diagnostics['eligible']}")

    return eligible


def rebuild_execution_state(
    open_tasks,
    update_fn,
    max_best_next_actions=MAX_BEST_NEXT_ACTIONS,
):
    print("=== EXECUTION ENGINE V2 ACTIVE ===")

    if not open_tasks:
        print("[Execution Engine V2] No open tasks supplied")
        return []

    print(f"[Execution Engine V2] Tasks received: {len(open_tasks)}")

    execution_active_tasks = get_execution_active_tasks(open_tasks)

    print("\\n--- Execution Engine V2 Sparse Reset ---")
    print(
        f"[Execution Engine V2] Previously persisted tasks: "
        f"{len(execution_active_tasks)}"
    )

    reset_count = 0

    for task in execution_active_tasks:
        try:
            task_id = task["id"]

            reset_properties = {
                "Execution Score": {"number": None},
                "Execution Rank": {"number": None},
            }

            success = safe_update_task(
                update_fn=update_fn,
                task_id=task_id,
                properties=reset_properties,
            )

            if success:
                reset_count += 1

        except Exception as e:
            print(f"[Execution Engine V2] reset failed: {e}")

    print(f"[Execution Engine V2] Reset tasks: {reset_count}")

    eligible_tasks = filter_execution_eligible_tasks(open_tasks)

    ranked = []

    for task in eligible_tasks:
        try:
            title = extract_title(task)


            orchestration = evaluate_execution_scoring(task)

            if EVALUATOR_AVAILABLE:

                # --------------------------------------------------
                # PRIMARY EVALUATOR AUTHORITY
                # --------------------------------------------------

                score = orchestration.evaluator_score

                reasons = [
                    c.name
                    for c in orchestration.evaluator_components
                ]

                # --------------------------------------------------
                # FALLBACK EXECUTION PATH
                # --------------------------------------------------
                #
                # Previously, tasks that received no evaluator
                # components collapsed silently to:
                #
                # -> 0 ()
                #
                # without:
                # - Ranking Shadow V3
                # - evaluator decomposition
                # - baseline cognition
                #
                # This created split cognition authority and made
                # legitimate executable tasks appear cognitively dead.
                #
                # If evaluator returns 0:
                # 1. Prefer legacy execution signals if available
                # 2. Otherwise apply lightweight executable baseline
                #
                # This preserves calmness while preventing silent
                # starvation of reasonable human tasks.

                if score == 0:

                    if orchestration.legacy_score > 0:

                        score = orchestration.legacy_score
                        reasons = orchestration.legacy_reasons

                        if _verbose_execution_diagnostics_enabled():
                            print(
                                "[Execution Engine V2] "
                                "fallback_to_legacy_scoring: "
                                f"{title} -> {score} "
                                f"({', '.join(reasons)})"
                            )

                    else:

                        structurally_reasonable = (
                            len(title.strip().split()) >= 3
                        )

                        if structurally_reasonable:

                            score = 1
                            reasons = ["baseline_executable"]

                            if _verbose_execution_diagnostics_enabled():
                                print(
                                    "[Execution Engine V2] "
                                    "baseline_executable_fallback: "
                                    f"{title} -> {score} "
                                    f"({', '.join(reasons)})"
                                )

            else:
                score = orchestration.legacy_score
                reasons = orchestration.legacy_reasons

#            print(
#                f"[Execution Engine V2] scoring: "
#                f"{title} -> {score} "
#                f"({', '.join(reasons)})"
#            )

            ranked.append({
                "task": task,
                "title": title,
                "score": score,
                "reasons": reasons,
                "legacy_score": orchestration.legacy_score,
                "evaluator_score": orchestration.evaluator_score,
                "divergence": orchestration.divergence,
            })


        except Exception as e:
            print(f"[Execution Engine V2] task scoring failed: {e}")

    ranked.sort(
        key=lambda x: (
            -x["score"],
            x["title"].lower(),
            x.get("page_id", "")
        )
    )

#    print("\\n--- Execution Engine V2 In-Memory Rankings ---")
#
#    for idx, item in enumerate(ranked[:15], start=1):
#        print(
#            f"rank={idx} "
#            f"score={item['score']} "
#            f"title={item['title']}"
#        )

    try:
        limit = int(max_best_next_actions)

    except Exception:
        limit = MAX_BEST_NEXT_ACTIONS

    print(f"[Execution Engine V2] Winner limit: {limit}")
    print("[Execution Engine V2] Persisting top 10 execution rankings only")

    winners = ranked[:limit]

    emit_evaluator_tuning_telemetry(ranked, winners)

    print("\\n--- Best Next Actions ---")

    for idx, item in enumerate(winners, start=1):
        print(
            f"BNA rank={idx} "
            f"score={item['score']} "
            f"title={item['title']}"
        )

    updated = 0

    persisted_ranked = ranked[:10]

    for rank_position, item in enumerate(persisted_ranked, start=1):
        try:
            task = item["task"]
            task_id = task["id"]

            properties = {
                "Execution Score": {
                    "number": item["score"]
                },
                "Execution Rank": {
                    "number": rank_position
                },
            }

            success = safe_update_task(
                update_fn=update_fn,
                task_id=task_id,
                properties=properties,
            )

            if success:
                updated += 1

        except Exception as e:
            print(f"[Execution Engine V2] reconciliation failed: {e}")

    print(f"\\n[Execution Engine V2] Tasks updated: {updated}")
    print("[Execution Engine V2] Reconciliation complete")

    return winners