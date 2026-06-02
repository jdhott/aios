"""Read-only historical project affinity telemetry for AIOS.

D1 scope:
- observes historical/completed task/project affinity
- emits compact telemetry
- performs no Notion writes
- does not affect execution ranking, BNA, Quick Wins, or governance reconciliation

D1.3 adds display-name resolution for Project relation page IDs so telemetry can show
human-readable project neighborhoods instead of raw Notion relation IDs.

D1.4 adds read-only active-task affinity previews: current open tasks are compared
against historical neighborhoods and printed as candidate matches only. These previews
are observational telemetry and never mutate Notion.

D1.5 adds weak-term weighting and evidence gating so broad one-word matches such as
"bread" or generic action verbs cannot create high-confidence active-task candidates by
themselves.

D1.6 adds strong-domain confidence calibration so specific operational anchor terms
like "pool", "skimmer", "workshop", and "labels" can produce high-confidence
previews even when the active task has one dominant, highly specific overlap term.

D1.7 adds runner-up and ambiguity telemetry for active-task previews. It still makes
no writes; it only surfaces when a second historical neighborhood is close enough
to make future write-back risky.

D1.8 adds duplicate/overlapping project-neighborhood detection. It compares
historical neighborhood term profiles and reports likely duplicate or overlapping
project concepts before any future project write-back phase.

D1.9 adds read-only canonical project consolidation suggestions. It groups
overlapping neighborhoods, selects a likely canonical project label, and reports
which shadow/suggested neighborhoods may be candidates for manual consolidation.
It performs no merges and no task/project mutation.

D2.1 adds longitudinal Suggested Project stability telemetry. It compares
current staged Suggested Project values against fresh affinity previews to detect
stable matches, drift, and new suggestions before broader persistence expansion.

D2.4 adds stability-governed persistence.

D2.5 adds normal-runtime compact summary support via the report wrapper. It uses read-only
canonical preference signals to classify staged Suggested Project writes more
conservatively, suppressing weak/shadow/ambiguous project-memory writes before
any future relation mutation.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import re
from typing import Any, Dict, List, Mapping, Sequence, Tuple


_STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "for", "of", "in", "on", "at", "with",
    "from", "by", "about", "into", "up", "out", "over", "under", "new", "old",
    "task", "tasks", "todo", "do", "make", "get", "set", "check", "review", "update",
    "create", "add", "fix", "clean", "prepare", "finish", "complete", "work", "next",
    "send", "sent", "message", "messages", "email", "emails", "call", "calls", "text",
    "put", "take", "move", "bring", "start", "open", "close", "done", "today",
}

# Weak terms are allowed to appear in neighborhood summaries, but they are deliberately
# discounted for active-task matching. These are usually brand/domain umbrella words or
# generic workflow words that are useful context but too broad to carry affinity alone.
_WEAK_TERMS = {
    "bread", "bakery", "solara", "community", "app", "basket", "order", "orders",
    "pickup", "delivery", "print", "printed", "printing", "bag", "bags",
    "basement", "kitchen", "home", "house", "car", "costco", "grocery", "groceries",
}

_STRONG_SIGNAL_TERMS = {
    "pool", "skimmer", "chlorine", "filter", "vacuum", "workshop", "label", "labels", "pizza", "teaching",
    "school", "recipe", "granola", "documentation", "stickers", "packaging", "oatmeal",
    "molasses", "ingredients", "flour", "milling", "starter", "levain", "dough",
    "chemicals", "dishes", "dishwasher", "storage", "equipment",
}

# Anchor terms are specific enough to carry project affinity by themselves when they
# appear repeatedly in a historical neighborhood. This avoids under-confidence on
# clear matches like "Organize pool equipment" while still suppressing broad terms
# such as "bread" or generic verbs.
_ANCHOR_DOMAIN_TERMS = {
    "pool", "skimmer", "chlorine", "filter", "vacuum",
    "workshop", "labels", "label", "stickers", "packaging",
    "school", "recipe", "granola", "dishwasher", "dishes",
}


def is_anchor_domain_term(term: str) -> bool:
    return term in _ANCHOR_DOMAIN_TERMS


def term_affinity_weight(term: str) -> int:
    """Return a conservative active-affinity weight for a token."""
    if term in _WEAK_TERMS:
        return 1
    if term in _STRONG_SIGNAL_TERMS:
        return 3
    return 2

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9'_-]{2,}")


def normalize_notion_id(value: str) -> str:
    """Normalize Notion page/database IDs to dashed UUID format when possible."""
    raw = (value or "").strip().strip('"').strip("'")
    compact = raw.replace("-", "")
    if len(compact) == 32:
        return f"{compact[0:8]}-{compact[8:12]}-{compact[12:16]}-{compact[16:20]}-{compact[20:32]}"
    return raw


def tokenize_title(text: str) -> List[str]:
    """Tokenize task titles for lightweight operational-neighborhood analysis."""
    tokens = []
    for raw in _TOKEN_RE.findall(text or ""):
        token = raw.lower().strip("'_- ")
        if token and token not in _STOPWORDS and len(token) >= 3:
            tokens.append(token)
    return tokens


def notion_title_plain_text(prop: Mapping[str, Any]) -> str:
    items = prop.get("title") or []
    return "".join(part.get("plain_text", "") for part in items if isinstance(part, Mapping)).strip()


def notion_rich_text_plain_text(prop: Mapping[str, Any]) -> str:
    items = prop.get("rich_text") or []
    return "".join(part.get("plain_text", "") for part in items if isinstance(part, Mapping)).strip()


def notion_checkbox(prop: Mapping[str, Any]) -> bool:
    return bool(prop.get("checkbox"))


def notion_select_name(prop: Mapping[str, Any]) -> str:
    selected = prop.get("select") or {}
    return str(selected.get("name") or "").strip()


def notion_relation_ids(prop: Mapping[str, Any]) -> List[str]:
    relation = prop.get("relation") or []
    return [normalize_notion_id(str(item.get("id"))) for item in relation if isinstance(item, Mapping) and item.get("id")]


def notion_page_title(page: Mapping[str, Any]) -> str:
    """Extract the first title property from a Notion page, regardless of property name."""
    props = page.get("properties") or {}
    for prop in props.values():
        if isinstance(prop, Mapping) and prop.get("type") == "title":
            title = notion_title_plain_text(prop)
            if title:
                return title
    return ""


@dataclass(frozen=True)
class HistoricalTask:
    id: str
    title: str
    done: bool = False
    archived: bool = False
    project_ids: Tuple[str, ...] = ()
    suggested_project: str = ""

    @property
    def project_key(self) -> str:
        if self.project_ids:
            return "relation:" + ",".join(sorted(self.project_ids))
        if self.suggested_project:
            return "suggested:" + self.suggested_project.strip().lower()
        return "unassigned"

    @property
    def is_historical(self) -> bool:
        return self.done or self.archived

    @property
    def is_active(self) -> bool:
        return not self.done and not self.archived


@dataclass(frozen=True)
class AffinitySummary:
    total_tasks: int
    historical_tasks: int
    active_tasks: int
    project_groups: int
    unassigned_historical_tasks: int
    top_project_neighborhoods: List[Dict[str, Any]]
    top_global_terms: List[Tuple[str, int]]
    active_task_previews: List[Dict[str, Any]]
    overlapping_neighborhoods: List[Dict[str, Any]]
    consolidation_suggestions: List[Dict[str, Any]]
    suggested_project_write_plan: List[Dict[str, Any]]
    suggested_project_suppressed: List[Dict[str, Any]]
    suggested_project_stability: Dict[str, Any]
    canonical_project_preferences: Dict[str, Any]
    canonical_preference_assistance: Dict[str, Any]
    stability_governed_persistence: Dict[str, Any]

    def telemetry_lines(self) -> List[str]:
        lines = [
            "=== PROJECT COGNITION — D2.5: STABILITY-GOVERNED SUGGESTED PROJECT PERSISTENCE ===",
            f"[Project Cognition] Historical tasks observed: {self.historical_tasks}/{self.total_tasks}",
            f"[Project Cognition] Active tasks observed: {self.active_tasks}/{self.total_tasks}",
            f"[Project Cognition] Project affinity groups: {self.project_groups}; unassigned_historical={self.unassigned_historical_tasks}",
        ]
        if self.top_global_terms:
            terms = ", ".join(f"{term}:{count}" for term, count in self.top_global_terms[:10])
            lines.append(f"[Project Cognition] Top historical terms: {terms}")
        for item in self.top_project_neighborhoods[:8]:
            terms = ", ".join(f"{term}:{count}" for term, count in item["terms"][:6])
            label = item.get("project_label") or item.get("project_key") or "(unknown)"
            key = item.get("project_key", "")
            if key.startswith("relation:") and label != key:
                lines.append(
                    "[Project Cognition] Neighborhood Project: "
                    f"{label} — tasks={item['task_count']}; terms={terms}"
                )
            else:
                lines.append(
                    "[Project Cognition] Neighborhood "
                    f"{label} — tasks={item['task_count']}; terms={terms}"
                )

        if self.active_task_previews:
            lines.append(
                "[Project Cognition] Active affinity preview: "
                f"candidates={len(self.active_task_previews)}; read_only=true"
            )
            for item in self.active_task_previews[:8]:
                overlap = ", ".join(item.get("overlap_terms", [])[:5])
                runner = item.get("runner_up") or {}
                ambiguity = item.get("ambiguity", "none")
                margin = item.get("runner_up_margin")
                runner_text = ""
                if runner:
                    runner_text = (
                        f"; runner_up={runner.get('project_label')}"
                        f" score={runner.get('score')}"
                        f" margin={margin}"
                        f" ambiguity={ambiguity}"
                    )
                lines.append(
                    "[Project Cognition] Active candidate: "
                    f"{item['task_title']} → {item['project_label']} "
                    f"(confidence={item['confidence']}; score={item['score']}; overlap={overlap}{runner_text})"
                )
        else:
            lines.append("[Project Cognition] Active affinity preview: candidates=0; read_only=true")

        if self.overlapping_neighborhoods:
            lines.append(
                "[Project Cognition] Overlapping project neighborhoods: "
                f"candidates={len(self.overlapping_neighborhoods)}; read_only=true"
            )
            for item in self.overlapping_neighborhoods[:6]:
                shared = ", ".join(item.get("shared_terms", [])[:6])
                lines.append(
                    "[Project Cognition] Overlap candidate: "
                    f"{item['left_label']} ↔ {item['right_label']} "
                    f"(overlap={item['overlap_score']:.2f}; shared={shared}; risk={item['risk']})"
                )
        else:
            lines.append("[Project Cognition] Overlapping project neighborhoods: candidates=0; read_only=true")

        if self.consolidation_suggestions:
            lines.append(
                "[Project Cognition] Canonical consolidation suggestions: "
                f"candidates={len(self.consolidation_suggestions)}; read_only=true"
            )
            for item in self.consolidation_suggestions[:6]:
                absorbs = ", ".join(item.get("absorbs", [])[:4])
                terms = ", ".join(item.get("shared_terms", [])[:5])
                lines.append(
                    "[Project Cognition] Consolidation suggestion: "
                    f"canonical={item['canonical_label']} absorbs={absorbs} "
                    f"(risk={item['risk']}; overlaps={item['overlap_count']}; shared={terms}; action=manual_review_only)"
                )
        else:
            lines.append("[Project Cognition] Canonical consolidation suggestions: candidates=0; read_only=true")

        lines.append("[Project Cognition] Affinity weighting: weak_terms_discounted=true; one_word_broad_matches_suppressed=true")
        ambiguous_count = sum(1 for item in self.active_task_previews if item.get("ambiguity") in {"medium", "high"})
        lines.append("[Project Cognition] Strong-domain confidence: anchor_terms_enabled=true; threshold=14; broad_terms_still_suppressed=true")
        lines.append(f"[Project Cognition] Runner-up ambiguity: enabled=true; ambiguous_candidates={ambiguous_count}; writeback_guard=active")
        lines.append(f"[Project Cognition] Project overlap detection: enabled=true; overlap_candidates={len(self.overlapping_neighborhoods)}; writeback_guard=active")
        lines.append(f"[Project Cognition] Consolidation suggestions: enabled=true; suggestions={len(self.consolidation_suggestions)}; writeback_guard=active")

        if self.suggested_project_write_plan or self.suggested_project_suppressed:
            lines.append(
                "[Project Cognition] Suggested Project persistence preview: "
                f"write_candidates={len(self.suggested_project_write_plan)}; "
                f"suppressed={len(self.suggested_project_suppressed)}; full_plan=explicit_only"
            )
            for item in self.suggested_project_write_plan[:8]:
                lines.append(
                    "[Project Cognition] Suggested Project write candidate: "
                    f"{item['task_title']} → {item['suggested_project']} "
                    f"(confidence={item['confidence']}; ambiguity={item['ambiguity']}; reason={item['reason']}; action=staging_field_only)"
                )
            for item in self.suggested_project_suppressed[:8]:
                lines.append(
                    "[Project Cognition] Suggested Project suppressed: "
                    f"{item['task_title']} → {item.get('suggested_project', item.get('project_label', '(unknown)'))} "
                    f"(reason={item['reason']}; confidence={item.get('confidence')}; ambiguity={item.get('ambiguity')})"
                )
        else:
            lines.append("[Project Cognition] Suggested Project persistence preview: write_candidates=0; suppressed=0; full_plan=explicit_only")

        stability = self.suggested_project_stability or {}
        lines.append(
            "[Project Cognition] Suggested Project stability telemetry: "
            f"enabled={str(bool(stability.get('enabled'))).lower()}; "
            f"preview_candidates={stability.get('preview_candidates', 0)}; "
            f"existing_suggestions={stability.get('existing_suggestions', 0)}; "
            f"stable_matches={stability.get('stable_matches', 0)}; "
            f"drift_candidates={stability.get('drift_candidates', 0)}; "
            f"new_suggestions={stability.get('new_suggestions', 0)}; writeback_guard=active"
        )
        for item in (stability.get("project_stability") or [])[:6]:
            stable_value = item.get("stability")
            stable_text = "n/a" if stable_value is None else f"{stable_value:.2f}"
            lines.append(
                "[Project Cognition] Suggested Project stability: "
                f"project={item.get('project')} stability={stable_text}; "
                f"repeated_matches={item.get('stable_matches', 0)}; "
                f"drift={item.get('drift_candidates', 0)}; "
                f"new={item.get('new_suggestions', 0)}"
            )
        for item in (stability.get("drift_examples") or [])[:4]:
            lines.append(
                "[Project Cognition] Suggested Project drift: "
                f"{item.get('task_title')} existing={item.get('existing_suggested_project')} "
                f"proposed={item.get('proposed_suggested_project')} "
                f"(confidence={item.get('confidence')}; ambiguity={item.get('ambiguity')})"
            )

        preferences = self.canonical_project_preferences or {}
        lines.append(
            "[Project Cognition] Canonical project preference memory: "
            f"enabled={str(bool(preferences.get('enabled'))).lower()}; "
            f"preferences={len(preferences.get('preferences') or [])}; "
            f"drift_dampening=preview_only; writeback_guard=active"
        )
        for item in (preferences.get("preferences") or [])[:6]:
            absorbs = ", ".join(item.get("absorbs", [])[:4])
            evidence = ", ".join(item.get("evidence", [])[:4])
            lines.append(
                "[Project Cognition] Canonical preference: "
                f"canonical={item.get('canonical_project')} strength={item.get('preference_strength'):.2f}; "
                f"absorbs={absorbs or 'none'}; evidence={evidence or 'none'}; "
                f"action=manual_review_only"
            )

        assistance = self.canonical_preference_assistance or {}
        lines.append(
            "[Project Cognition] Canonical preference assisted suppression: "
            f"enabled={str(bool(assistance.get('enabled'))).lower()}; "
            f"safe_candidates={assistance.get('safe_candidates', 0)}; "
            f"suppressed_by_preference={assistance.get('suppressed_by_preference', 0)}; "
            f"shadow_suppressed={assistance.get('shadow_suppressed', 0)}; "
            f"weak_preference_suppressed={assistance.get('weak_preference_suppressed', 0)}; "
            "writeback_guard=active"
        )

        sgp = self.stability_governed_persistence or {}
        lines.append(
            "[Project Cognition] Stability-governed Suggested Project persistence: "
            f"enabled={str(bool(sgp.get('enabled'))).lower()}; "
            f"auto_apply_default={str(bool(sgp.get('auto_apply_default'))).lower()}; "
            f"eligible={len(sgp.get('eligible_writes') or [])}; "
            f"suppressed={len(sgp.get('suppressed') or [])}; "
            f"threshold={sgp.get('stability_threshold', 0)}; "
            "project_relation_mutation=disabled; execution_authority_impact=none"
        )
        for item in (sgp.get("eligible_writes") or [])[:6]:
            lines.append(
                "[Project Cognition] Stability-governed write eligible: "
                f"{item.get('task_title')} → {item.get('suggested_project')} "
                f"(stability={item.get('project_stability')}; repeated={item.get('stable_matches')}; "
                f"reason={item.get('reason')}; action=staging_field_only)"
            )
        for item in (sgp.get("suppressed") or [])[:4]:
            lines.append(
                "[Project Cognition] Stability-governed write suppressed: "
                f"{item.get('task_title')} → {item.get('suggested_project')} "
                f"(reason={item.get('suppression_reason')}; stability={item.get('project_stability')}; "
                f"repeated={item.get('stable_matches')})"
            )

        lines.append("[Project Cognition] D2.4 mode: stability_governed_auto_writes=true; writes=bounded_to_stable_low_ambiguity_suggestions; project_relation_mutation=disabled; execution_authority_impact=none")
        return lines


def project_key_label(project_key: str, project_name_by_id: Mapping[str, str] | None = None) -> str:
    """Return a human-readable project/neighborhood label for telemetry."""
    project_name_by_id = project_name_by_id or {}
    if project_key.startswith("relation:"):
        raw_ids = [normalize_notion_id(item) for item in project_key.removeprefix("relation:").split(",") if item]
        names = [project_name_by_id.get(pid, "").strip() for pid in raw_ids]
        names = [name for name in names if name]
        if names:
            return " + ".join(names)
        if raw_ids:
            return "unresolved_relation:" + ",".join(raw_ids)
    if project_key.startswith("suggested:"):
        return "suggested:" + project_key.removeprefix("suggested:")
    return project_key


def _confidence_for_score(
    score: int,
    *,
    strong_terms: int = 0,
    evidence_terms: int = 0,
    anchor_terms: int = 0,
) -> str:
    """Convert affinity score into conservative preview confidence.

    D1.6.1 allows one highly specific anchor-domain term to produce high confidence
    when historical support is strong enough for compact previews. Broad/weak terms
    remain unable to do this.
    """
    if score >= 14 and anchor_terms >= 1:
        return "high"
    if score >= 16 and strong_terms >= 1 and evidence_terms >= 2:
        return "high"
    if score >= 8 and (strong_terms >= 1 or evidence_terms >= 3):
        return "medium"
    return "low"


def _ambiguity_level(best_score: int, runner_score: int, runner_confidence: str) -> str:
    """Classify runner-up risk for future write-back review.

    This is intentionally conservative and read-only. It does not suppress the
    preview; it only annotates whether the preview would need caution before a
    future mutation phase.
    """
    if runner_score <= 0:
        return "none"
    margin = best_score - runner_score
    if runner_confidence == "high" and margin <= 6:
        return "high"
    if runner_confidence in {"high", "medium"} and margin <= 10:
        return "medium"
    return "low"



def _neighborhood_term_map(neighborhood: Mapping[str, Any]) -> Dict[str, int]:
    """Return weighted terms for overlap detection, excluding weak umbrella terms."""
    result: Dict[str, int] = {}
    for term, count in neighborhood.get("terms") or []:
        term = str(term)
        if term in _WEAK_TERMS:
            continue
        weight = term_affinity_weight(term)
        if weight <= 1:
            continue
        result[term] = min(int(count), 8) * weight
    return result


def _weighted_jaccard(left: Mapping[str, int], right: Mapping[str, int]) -> float:
    terms = set(left) | set(right)
    if not terms:
        return 0.0
    numerator = sum(min(int(left.get(term, 0)), int(right.get(term, 0))) for term in terms)
    denominator = sum(max(int(left.get(term, 0)), int(right.get(term, 0))) for term in terms)
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _overlap_risk(score: float, shared_terms: Sequence[str]) -> str:
    anchor_shared = [term for term in shared_terms if is_anchor_domain_term(term)]
    if score >= 0.45 or (score >= 0.30 and len(anchor_shared) >= 2):
        return "high"
    if score >= 0.22 or anchor_shared:
        return "medium"
    return "low"


def detect_overlapping_neighborhoods(
    neighborhoods: Sequence[Mapping[str, Any]],
    *,
    min_overlap_score: float = 0.18,
    max_pairs: int = 10,
) -> List[Dict[str, Any]]:
    """Detect likely duplicate or overlapping project neighborhoods.

    This is read-only telemetry. It intentionally uses weighted term-profile overlap
    rather than title equality so duplicate concepts can emerge from history
    without hardcoded project names.
    """
    profiles = []
    for neighborhood in neighborhoods:
        term_map = _neighborhood_term_map(neighborhood)
        if term_map:
            profiles.append((neighborhood, term_map))

    overlaps: List[Dict[str, Any]] = []
    for index, (left, left_terms) in enumerate(profiles):
        for right, right_terms in profiles[index + 1:]:
            shared_terms = sorted(
                set(left_terms) & set(right_terms),
                key=lambda term: (is_anchor_domain_term(term), min(left_terms.get(term, 0), right_terms.get(term, 0))),
                reverse=True,
            )
            if not shared_terms:
                continue
            score = _weighted_jaccard(left_terms, right_terms)
            if score < min_overlap_score and not any(is_anchor_domain_term(term) for term in shared_terms):
                continue
            risk = _overlap_risk(score, shared_terms)
            if risk == "low" and score < min_overlap_score:
                continue
            overlaps.append({
                "left_key": left.get("project_key", ""),
                "left_label": left.get("project_label") or left.get("project_key") or "(unknown)",
                "right_key": right.get("project_key", ""),
                "right_label": right.get("project_label") or right.get("project_key") or "(unknown)",
                "overlap_score": round(score, 3),
                "shared_terms": shared_terms,
                "risk": risk,
            })

    risk_rank = {"high": 3, "medium": 2, "low": 1}
    overlaps.sort(key=lambda item: (risk_rank.get(item["risk"], 0), item["overlap_score"], len(item["shared_terms"])), reverse=True)
    return overlaps[:max_pairs]



def _canonical_priority(neighborhood: Mapping[str, Any]) -> Tuple[int, int, str]:
    """Prefer real relation-backed projects, larger histories, then stable labels."""
    key = str(neighborhood.get("project_key") or "")
    label = str(neighborhood.get("project_label") or key)
    is_relation = key.startswith("relation:")
    is_suggested = key.startswith("suggested:")
    return (1 if is_relation and not is_suggested else 0, int(neighborhood.get("task_count") or 0), label.lower())


def suggest_canonical_consolidations(
    neighborhoods: Sequence[Mapping[str, Any]],
    overlaps: Sequence[Mapping[str, Any]],
    *,
    max_suggestions: int = 8,
) -> List[Dict[str, Any]]:
    """Suggest manual canonicalization candidates from overlapping neighborhoods.

    This is deliberately read-only. It does not merge projects, rewrite Suggested
    Project values, or update task relations. The output is a manual-review signal
    for future governed write-back design.
    """
    by_key = {str(n.get("project_key") or ""): n for n in neighborhoods if n.get("project_key")}
    parent: Dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    useful_overlaps = []
    for item in overlaps:
        left = str(item.get("left_key") or "")
        right = str(item.get("right_key") or "")
        if not left or not right or left not in by_key or right not in by_key:
            continue
        if str(item.get("risk")) not in {"medium", "high"}:
            continue
        useful_overlaps.append(item)
        union(left, right)

    clusters: Dict[str, List[str]] = defaultdict(list)
    for item in useful_overlaps:
        clusters[find(str(item.get("left_key")))].append(str(item.get("left_key")))
        clusters[find(str(item.get("right_key")))].append(str(item.get("right_key")))

    suggestions: List[Dict[str, Any]] = []
    for keys in clusters.values():
        unique_keys = sorted(set(keys))
        if len(unique_keys) < 2:
            continue
        members = [by_key[key] for key in unique_keys]
        canonical = sorted(members, key=_canonical_priority, reverse=True)[0]
        canonical_key = str(canonical.get("project_key") or "")
        absorbs = [str(member.get("project_label") or member.get("project_key")) for member in members if member.get("project_key") != canonical_key]
        cluster_overlaps = [
            item for item in useful_overlaps
            if str(item.get("left_key")) in unique_keys and str(item.get("right_key")) in unique_keys
        ]
        shared_counter: Counter[str] = Counter()
        high_seen = False
        for item in cluster_overlaps:
            shared_counter.update(item.get("shared_terms") or [])
            high_seen = high_seen or item.get("risk") == "high"
        suggestions.append({
            "canonical_key": canonical_key,
            "canonical_label": str(canonical.get("project_label") or canonical_key),
            "absorbs": absorbs,
            "shared_terms": [term for term, _ in shared_counter.most_common(8)],
            "risk": "high" if high_seen else "medium",
            "overlap_count": len(cluster_overlaps),
            "read_only": True,
            "action": "manual_review_only",
        })

    risk_rank = {"high": 2, "medium": 1}
    suggestions.sort(key=lambda item: (risk_rank.get(item["risk"], 0), item["overlap_count"], len(item["absorbs"])), reverse=True)
    return suggestions[:max_suggestions]


def _project_keys_in_consolidation_risk(suggestions: Sequence[Mapping[str, Any]]) -> set[str]:
    """Return project keys that are part of manual-review consolidation clusters."""
    keys: set[str] = set()
    for suggestion in suggestions:
        canonical = str(suggestion.get("canonical_key") or "")
        if canonical:
            keys.add(canonical)
        # D1.9 suggestions intentionally expose labels, not every absorbed key, so
        # write gating below also uses runner-up ambiguity. This function is kept
        # conservative for canonical relation keys we can identify exactly.
    return keys



def build_suggested_project_stability_telemetry(
    tasks: Sequence[HistoricalTask],
    active_previews: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Compare existing Suggested Project staging values to fresh affinity previews.

    This is telemetry only. It does not decide writes. It gives us a longitudinal
    safety signal: if the same task already carries the same staged suggestion that
    the current affinity pass would make, the suggestion is considered stable. If a
    task already has a different staged suggestion, it is drift and should remain
    guarded before broader write-back.
    """
    task_by_id = {task.id: task for task in tasks if task.id}
    stable_examples: List[Dict[str, Any]] = []
    drift_examples: List[Dict[str, Any]] = []
    new_examples: List[Dict[str, Any]] = []
    project_counts: Dict[str, Counter[str]] = defaultdict(Counter)

    for preview in active_previews:
        task_id = str(preview.get("task_id") or "")
        task = task_by_id.get(task_id)
        if not task:
            continue
        existing = (task.suggested_project or "").strip()
        proposed = str(preview.get("project_label") or "").strip()
        if not proposed:
            continue
        base = {
            "task_id": task_id,
            "task_title": task.title,
            "existing_suggested_project": existing,
            "proposed_suggested_project": proposed,
            "confidence": preview.get("confidence"),
            "ambiguity": preview.get("ambiguity", "none"),
        }
        if existing and existing.lower() == proposed.lower():
            stable_examples.append({**base, "status": "stable_match"})
            project_counts[proposed]["stable"] += 1
        elif existing:
            drift_examples.append({**base, "status": "drift"})
            project_counts[proposed]["drift"] += 1
        else:
            new_examples.append({**base, "status": "new_suggestion"})
            project_counts[proposed]["new"] += 1

    project_stability: List[Dict[str, Any]] = []
    for project, counts in project_counts.items():
        stable = int(counts.get("stable", 0))
        drift = int(counts.get("drift", 0))
        new = int(counts.get("new", 0))
        denominator = stable + drift
        stability = round(stable / denominator, 2) if denominator else None
        if denominator or new:
            project_stability.append({
                "project": project,
                "stable_matches": stable,
                "drift_candidates": drift,
                "new_suggestions": new,
                "stability": stability,
            })
    project_stability.sort(key=lambda item: ((item["stability"] is not None, item["stability"] or 0), item["stable_matches"], item["new_suggestions"]), reverse=True)

    return {
        "enabled": True,
        "preview_candidates": len(active_previews),
        "existing_suggestions": len(stable_examples) + len(drift_examples),
        "stable_matches": len(stable_examples),
        "drift_candidates": len(drift_examples),
        "new_suggestions": len(new_examples),
        "stable_examples": stable_examples[:6],
        "drift_examples": drift_examples[:6],
        "new_examples": new_examples[:6],
        "project_stability": project_stability[:8],
        "writeback_guard": "active",
    }



def build_canonical_project_preference_memory(
    consolidation_suggestions: Sequence[Mapping[str, Any]],
    suggested_project_stability: Mapping[str, Any],
) -> Dict[str, Any]:
    """Derive read-only canonical project preference signals.

    D2.4 does not mutate projects or tasks. It creates a governance-memory preview
    that answers: when project neighborhoods conflict, which canonical label looks
    most stable and should be preferred by future guarded write-back?
    """
    stability_by_project: Dict[str, Mapping[str, Any]] = {
        str(item.get("project") or ""): item
        for item in (suggested_project_stability.get("project_stability") or [])
        if item.get("project")
    }
    drift_toward: Counter[str] = Counter()
    drift_from: Counter[str] = Counter()
    for item in (suggested_project_stability.get("drift_examples") or []):
        proposed = str(item.get("proposed_suggested_project") or "").strip()
        existing = str(item.get("existing_suggested_project") or "").strip()
        if proposed:
            drift_toward[proposed] += 1
        if existing:
            drift_from[existing] += 1

    preferences: List[Dict[str, Any]] = []
    for suggestion in consolidation_suggestions:
        canonical = str(suggestion.get("canonical_label") or "").strip()
        if not canonical:
            continue
        stability = stability_by_project.get(canonical, {})
        stable_matches = int(stability.get("stable_matches") or 0)
        drift_candidates = int(stability.get("drift_candidates") or 0)
        new_suggestions = int(stability.get("new_suggestions") or 0)
        overlap_count = int(suggestion.get("overlap_count") or 0)
        absorbs = [str(item) for item in (suggestion.get("absorbs") or []) if item]
        drift_to = int(drift_toward.get(canonical, 0))

        # Conservative bounded score. This is a preference signal, not authority.
        raw = (
            0.12 * min(overlap_count, 8)
            + 0.10 * min(len(absorbs), 5)
            + 0.10 * min(stable_matches, 5)
            + 0.08 * min(new_suggestions, 5)
            + 0.08 * min(drift_to, 5)
            - 0.06 * min(drift_candidates, 5)
        )
        strength = max(0.0, min(1.0, round(raw, 2)))
        evidence: List[str] = []
        if overlap_count:
            evidence.append(f"overlaps:{overlap_count}")
        if absorbs:
            evidence.append(f"absorbs:{len(absorbs)}")
        if stable_matches:
            evidence.append(f"stable:{stable_matches}")
        if drift_to:
            evidence.append(f"drift_toward:{drift_to}")
        if drift_candidates:
            evidence.append(f"drift_against:{drift_candidates}")

        preferences.append({
            "canonical_project": canonical,
            "canonical_key": suggestion.get("canonical_key", ""),
            "absorbs": absorbs,
            "preference_strength": strength,
            "evidence": evidence,
            "read_only": True,
            "action": "manual_review_only",
        })

    preferences.sort(key=lambda item: (item["preference_strength"], len(item.get("absorbs", []))), reverse=True)
    return {
        "enabled": True,
        "preferences": preferences[:8],
        "writeback_guard": "active",
        "project_relation_mutation": "disabled",
    }


def _canonical_preference_maps(
    canonical_project_preferences: Mapping[str, Any] | None,
) -> Tuple[Dict[str, Mapping[str, Any]], Dict[str, Mapping[str, Any]]]:
    """Return canonical and absorbed-label lookup maps for D2.4 write guards."""
    by_canonical: Dict[str, Mapping[str, Any]] = {}
    by_absorbed: Dict[str, Mapping[str, Any]] = {}
    for pref in (canonical_project_preferences or {}).get("preferences") or []:
        canonical = str(pref.get("canonical_project") or "").strip().lower()
        if canonical:
            by_canonical[canonical] = pref
        for absorbed in pref.get("absorbs") or []:
            label = str(absorbed or "").strip().lower()
            if label:
                by_absorbed[label] = pref
    return by_canonical, by_absorbed


def build_suggested_project_write_plan(
    active_previews: Sequence[Mapping[str, Any]],
    consolidation_suggestions: Sequence[Mapping[str, Any]],
    canonical_project_preferences: Mapping[str, Any] | None = None,
    *,
    allow_overlap_risk: bool = False,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """Classify active previews into dry-run Suggested Project write candidates.

    D2.4 uses canonical preference memory as a suppression aid only. It does not
    rewrite project labels, merge projects, mutate project relations, or create
    new Notion authority. It keeps high-confidence/low-ambiguity stable writes,
    suppresses shadow project targets, and requires manual review when a target
    belongs to a weak or fragmented canonical-preference cluster.
    """
    risky_keys = _project_keys_in_consolidation_risk(consolidation_suggestions)
    pref_by_canonical, pref_by_absorbed = _canonical_preference_maps(canonical_project_preferences)
    plan: List[Dict[str, Any]] = []
    suppressed: List[Dict[str, Any]] = []
    assisted_counts: Counter[str] = Counter()

    for preview in active_previews:
        confidence = str(preview.get("confidence") or "")
        ambiguity = str(preview.get("ambiguity") or "none")
        project_key = str(preview.get("project_key") or "")
        project_label = str(preview.get("project_label") or "")
        label_key = project_label.strip().lower()
        canonical_pref = pref_by_canonical.get(label_key)
        absorbed_pref = pref_by_absorbed.get(label_key)
        pref = canonical_pref or absorbed_pref
        pref_strength = float((pref or {}).get("preference_strength") or 0.0)
        base = {
            "task_id": str(preview.get("task_id") or ""),
            "task_title": str(preview.get("task_title") or ""),
            "project_key": project_key,
            "project_label": project_label,
            "suggested_project": project_label,
            "confidence": confidence,
            "ambiguity": ambiguity,
            "score": preview.get("score", 0),
            "canonical_preference_strength": pref_strength,
            "canonical_preference": (pref or {}).get("canonical_project", ""),
            "read_only_plan": True,
        }

        reason = ""
        if not base["task_id"]:
            reason = "missing_task_id"
        elif confidence != "high":
            reason = "confidence_not_high"
        elif ambiguity not in {"none", "low"}:
            reason = "canonical_preference_ambiguity_guard" if pref_strength >= 0.75 else "ambiguity_guard"
        elif not project_key.startswith("relation:"):
            reason = "suggested_or_unassigned_target_guard"
        elif absorbed_pref:
            reason = "shadow_project_guard"
        elif canonical_pref and pref_strength < 0.75:
            reason = "weak_canonical_preference_guard"
        elif project_key in risky_keys and not allow_overlap_risk:
            # D2.4 allows strong canonical preference to dampen overlap noise only
            # when the active-task match is otherwise very safe.
            if pref_strength >= 0.75 and ambiguity in {"none", "low"}:
                assisted_counts["overlap_dampened"] += 1
            else:
                reason = "consolidation_overlap_guard"
        elif project_label.startswith("suggested:") or project_label.startswith("unresolved_relation:"):
            reason = "non_canonical_label_guard"

        if reason:
            if reason in {"canonical_preference_ambiguity_guard", "shadow_project_guard", "weak_canonical_preference_guard"}:
                assisted_counts["suppressed_by_preference"] += 1
            if reason == "shadow_project_guard":
                assisted_counts["shadow_suppressed"] += 1
            if reason == "weak_canonical_preference_guard":
                assisted_counts["weak_preference_suppressed"] += 1
            suppressed.append({**base, "reason": reason})
        else:
            assisted_counts["safe_candidates"] += 1
            plan.append({**base, "reason": "safe_high_confidence_low_ambiguity"})

    assistance = {
        "enabled": True,
        "safe_candidates": len(plan),
        "suppressed_by_preference": int(assisted_counts.get("suppressed_by_preference", 0)),
        "shadow_suppressed": int(assisted_counts.get("shadow_suppressed", 0)),
        "weak_preference_suppressed": int(assisted_counts.get("weak_preference_suppressed", 0)),
        "overlap_dampened": int(assisted_counts.get("overlap_dampened", 0)),
        "writeback_guard": "active",
    }
    return plan, suppressed, assistance


def build_stability_governed_persistence_plan(
    suggested_project_write_plan: Sequence[Mapping[str, Any]],
    suggested_project_stability: Mapping[str, Any],
    canonical_project_preferences: Mapping[str, Any] | None = None,
    *,
    stability_threshold: float = 0.85,
    min_repeated_matches: int = 2,
) -> Dict[str, Any]:
    """Select the safest Suggested Project staging writes for D2.4 default persistence.

    This remains a staging-field-only authority. It never mutates project relations,
    never creates projects, and never affects execution ranking. A candidate must
    already pass the D2.3 write guards, then demonstrate longitudinal stability.
    """
    stability_by_project: Dict[str, Mapping[str, Any]] = {
        str(item.get("project") or "").strip().lower(): item
        for item in (suggested_project_stability.get("project_stability") or [])
        if item.get("project")
    }
    pref_by_canonical, _ = _canonical_preference_maps(canonical_project_preferences)
    eligible: List[Dict[str, Any]] = []
    suppressed: List[Dict[str, Any]] = []

    for item in suggested_project_write_plan:
        project = str(item.get("suggested_project") or item.get("project_label") or "").strip()
        project_key = project.lower()
        stability = stability_by_project.get(project_key, {})
        stable_value = stability.get("stability")
        stable_matches = int(stability.get("stable_matches") or 0)
        drift_candidates = int(stability.get("drift_candidates") or 0)
        pref = pref_by_canonical.get(project_key) or {}
        pref_strength = float(pref.get("preference_strength") or item.get("canonical_preference_strength") or 0.0)

        base = {
            **dict(item),
            "project_stability": stable_value,
            "stable_matches": stable_matches,
            "drift_candidates": drift_candidates,
            "canonical_preference_strength": pref_strength,
        }

        reason = ""
        if stable_value is None:
            reason = "no_longitudinal_stability_yet"
        elif float(stable_value) < stability_threshold:
            reason = "stability_below_threshold"
        elif stable_matches < min_repeated_matches:
            reason = "insufficient_repeated_matches"
        elif drift_candidates:
            reason = "drift_present"

        if reason:
            suppressed.append({**base, "suppression_reason": reason})
        else:
            eligible.append({**base, "reason": "stable_high_confidence_low_ambiguity"})

    return {
        "enabled": True,
        "auto_apply_default": True,
        "stability_threshold": stability_threshold,
        "min_repeated_matches": min_repeated_matches,
        "eligible_writes": eligible,
        "suppressed": suppressed,
        "writeback_guard": "active",
        "project_relation_mutation": "disabled",
        "execution_authority_impact": "none",
    }

def build_active_task_previews(
    tasks: Sequence[HistoricalTask],
    neighborhoods: Sequence[Mapping[str, Any]],
    *,
    min_score: int = 3,
    max_candidates: int = 12,
) -> List[Dict[str, Any]]:
    """Compare active tasks to historical neighborhoods and return read-only preview candidates.

    D1.7 keeps the best project-neighborhood match, but also records the nearest
    runner-up match and an ambiguity level. This gives us a safety signal before
    any future project write-back phase.
    """
    previews: List[Dict[str, Any]] = []
    active_tasks = [task for task in tasks if task.is_active and task.title]

    for task in active_tasks:
        task_tokens = Counter(tokenize_title(task.title))
        if not task_tokens:
            continue

        candidates: List[Dict[str, Any]] = []
        for neighborhood in neighborhoods:
            term_counts = dict(neighborhood.get("terms") or [])
            if not term_counts:
                continue
            overlap_terms = [term for term in task_tokens if term in term_counts]
            if not overlap_terms:
                continue
            strong_overlap_terms = [term for term in overlap_terms if term_affinity_weight(term) > 1]
            weak_overlap_terms = [term for term in overlap_terms if term_affinity_weight(term) == 1]
            anchor_overlap_terms = [term for term in overlap_terms if is_anchor_domain_term(term)]

            score = sum(
                min(int(term_counts.get(term, 0)), 5) * int(task_tokens[term]) * term_affinity_weight(term)
                for term in overlap_terms
            )
            evidence_terms = len(set(overlap_terms))
            has_strong_signal = bool(strong_overlap_terms)
            if not has_strong_signal and evidence_terms < 3:
                continue
            if score < min_score:
                continue
            candidates.append({
                "task_id": task.id,
                "task_title": task.title,
                "project_key": neighborhood.get("project_key", ""),
                "project_label": neighborhood.get("project_label") or neighborhood.get("project_key") or "(unknown)",
                "score": score,
                "confidence": _confidence_for_score(
                    score,
                    strong_terms=len(set(strong_overlap_terms)),
                    evidence_terms=evidence_terms,
                    anchor_terms=len(set(anchor_overlap_terms)),
                ),
                "overlap_terms": sorted(overlap_terms, key=lambda term: (term_affinity_weight(term), term_counts.get(term, 0)), reverse=True),
                "strong_overlap_terms": sorted(strong_overlap_terms),
                "weak_overlap_terms": sorted(weak_overlap_terms),
                "anchor_overlap_terms": sorted(anchor_overlap_terms),
            })

        if not candidates:
            continue

        candidates.sort(key=lambda item: (item["score"], item["confidence"], item["project_label"]), reverse=True)
        best = dict(candidates[0])
        runner = candidates[1] if len(candidates) > 1 else None
        if runner:
            margin = int(best["score"]) - int(runner["score"])
            best["runner_up"] = {
                "project_key": runner.get("project_key", ""),
                "project_label": runner.get("project_label", "(unknown)"),
                "score": runner.get("score", 0),
                "confidence": runner.get("confidence", "low"),
                "overlap_terms": runner.get("overlap_terms", []),
            }
            best["runner_up_margin"] = margin
            best["ambiguity"] = _ambiguity_level(int(best["score"]), int(runner.get("score", 0)), str(runner.get("confidence", "low")))
        else:
            best["runner_up"] = None
            best["runner_up_margin"] = None
            best["ambiguity"] = "none"
        previews.append(best)

    previews.sort(key=lambda item: (item["score"], item["task_title"].lower()), reverse=True)
    return previews[:max_candidates]

def summarize_historical_affinity(
    tasks: Sequence[HistoricalTask],
    *,
    min_group_tasks: int = 2,
    top_terms: int = 10,
    project_name_by_id: Mapping[str, str] | None = None,
    include_active_preview: bool = True,
    active_preview_min_score: int = 3,
    active_preview_limit: int = 12,
) -> AffinitySummary:
    """Build compact read-only affinity telemetry from historical task records."""
    historical = [task for task in tasks if task.is_historical]
    active = [task for task in tasks if task.is_active]
    grouped: Dict[str, List[HistoricalTask]] = defaultdict(list)
    global_terms: Counter[str] = Counter()

    for task in historical:
        grouped[task.project_key].append(task)
        global_terms.update(tokenize_title(task.title))

    neighborhoods: List[Dict[str, Any]] = []
    for project_key, project_tasks in grouped.items():
        if project_key == "unassigned" or len(project_tasks) < min_group_tasks:
            continue
        term_counts: Counter[str] = Counter()
        for task in project_tasks:
            term_counts.update(tokenize_title(task.title))
        neighborhoods.append({
            "project_key": project_key,
            "project_label": project_key_label(project_key, project_name_by_id),
            "task_count": len(project_tasks),
            "terms": term_counts.most_common(top_terms),
        })

    neighborhoods.sort(key=lambda item: (item["task_count"], len(item["terms"])), reverse=True)
    active_previews = []
    if include_active_preview:
        active_previews = build_active_task_previews(
            tasks,
            neighborhoods,
            min_score=active_preview_min_score,
            max_candidates=active_preview_limit,
        )
    overlapping_neighborhoods = detect_overlapping_neighborhoods(neighborhoods)
    consolidation_suggestions = suggest_canonical_consolidations(neighborhoods, overlapping_neighborhoods)
    suggested_project_stability = build_suggested_project_stability_telemetry(tasks, active_previews)
    canonical_project_preferences = build_canonical_project_preference_memory(
        consolidation_suggestions,
        suggested_project_stability,
    )
    (
        suggested_project_write_plan,
        suggested_project_suppressed,
        canonical_preference_assistance,
    ) = build_suggested_project_write_plan(
        active_previews,
        consolidation_suggestions,
        canonical_project_preferences,
    )
    stability_governed_persistence = build_stability_governed_persistence_plan(
        suggested_project_write_plan,
        suggested_project_stability,
        canonical_project_preferences,
    )

    return AffinitySummary(
        total_tasks=len(tasks),
        historical_tasks=len(historical),
        active_tasks=len(active),
        project_groups=len(neighborhoods),
        unassigned_historical_tasks=len(grouped.get("unassigned", [])),
        top_project_neighborhoods=neighborhoods,
        top_global_terms=global_terms.most_common(top_terms),
        active_task_previews=active_previews,
        overlapping_neighborhoods=overlapping_neighborhoods,
        consolidation_suggestions=consolidation_suggestions,
        suggested_project_write_plan=suggested_project_write_plan,
        suggested_project_suppressed=suggested_project_suppressed,
        suggested_project_stability=suggested_project_stability,
        canonical_project_preferences=canonical_project_preferences,
        canonical_preference_assistance=canonical_preference_assistance,
        stability_governed_persistence=stability_governed_persistence,
    )


def task_from_notion_page(
    page: Mapping[str, Any],
    *,
    title_property: str = "Task Name",
    done_property: str = "Done",
    project_property: str = "Project",
    suggested_project_property: str = "Suggested Project",
) -> HistoricalTask:
    props = page.get("properties") or {}
    title_prop = props.get(title_property) or {}
    title = notion_title_plain_text(title_prop)
    if not title:
        title = notion_page_title(page)
    done = notion_checkbox(props.get(done_property) or {})
    archived = bool(page.get("archived"))
    project_ids = tuple(notion_relation_ids(props.get(project_property) or {}))
    suggested = ""
    suggested_prop = props.get(suggested_project_property) or {}
    ptype = suggested_prop.get("type")
    if ptype == "rich_text":
        suggested = notion_rich_text_plain_text(suggested_prop)
    elif ptype == "select":
        suggested = notion_select_name(suggested_prop)
    return HistoricalTask(
        id=str(page.get("id") or ""),
        title=title,
        done=done,
        archived=archived,
        project_ids=project_ids,
        suggested_project=suggested,
    )
