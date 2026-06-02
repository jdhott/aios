"""
AIOS Runtime Analytics A1.1

Hardened read-only analytics ledger for execution/evaluator telemetry.
Writes:
- logs/runtime_analytics.csv
- logs/runtime_analytics_latest.json

A1.1 adds BNA metadata provenance mix from the existing AI Processing Log.
"""
from __future__ import annotations

import csv
import json
import os
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    import requests
except Exception:  # pragma: no cover - runtime dependency guard
    requests = None

VERSION = "aios-runtime-analytics-a1.1"
SUMMARY_MARKER = "AIOS RUNTIME ANALYTICS SUMMARY A1.1"


def _score_band(score: int) -> str:
    try:
        score = int(score or 0)
    except Exception:
        score = 0
    if score <= 3:
        return "low_1_3"
    if score <= 10:
        return "medium_4_10"
    if score <= 25:
        return "high_11_25"
    return "very_high_26_plus"


def _component_pairs(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        components = item.get("evaluator_components") or []
        for component in components:
            name = getattr(component, "name", None)
            score = getattr(component, "score", None)
            if name is not None:
                out.append({"name": str(name), "score": score})
        if out:
            return out

        reasons = item.get("reasons") or []
        for reason in reasons:
            out.append({"name": str(reason), "score": None})
    except Exception as exc:
        out.append({"name": "component_extract_failed", "score": str(exc)})
    return out


def _counter_from_reasons(items: Iterable[Dict[str, Any]]) -> Counter:
    counter: Counter = Counter()
    for item in items:
        for reason in item.get("reasons") or []:
            counter[str(reason)] += 1
    return counter


def _counter_from_score_bands(items: Iterable[Dict[str, Any]]) -> Counter:
    counter: Counter = Counter()
    for item in items:
        counter[_score_band(item.get("score", 0))] += 1
    return counter


def _scoring_sources(items: Iterable[Dict[str, Any]]) -> Counter:
    counter: Counter = Counter()
    for item in items:
        score = item.get("score", 0) or 0
        evaluator_score = item.get("evaluator_score", 0) or 0
        legacy_score = item.get("legacy_score", 0) or 0
        reasons = item.get("reasons") or []

        if reasons == ["baseline_executable"]:
            counter["baseline_fallback"] += 1
        elif evaluator_score and score == evaluator_score:
            counter["evaluator"] += 1
        elif legacy_score and score == legacy_score:
            counter["legacy_fallback"] += 1
        elif evaluator_score:
            counter["evaluator"] += 1
        elif legacy_score:
            counter["legacy_fallback"] += 1
        else:
            counter["zero_signal"] += 1
    return counter


def _safe_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _plain_text_property(prop: Any) -> str:
    if not isinstance(prop, dict):
        return ""
    if prop.get("type") == "title":
        parts = prop.get("title") or []
        return "".join(part.get("plain_text") or part.get("text", {}).get("content", "") for part in parts)
    if prop.get("type") == "rich_text":
        parts = prop.get("rich_text") or []
        return "".join(part.get("plain_text") or part.get("text", {}).get("content", "") for part in parts)
    if "title" in prop:
        return "".join(part.get("plain_text") or part.get("text", {}).get("content", "") for part in prop.get("title") or [])
    if "rich_text" in prop:
        return "".join(part.get("plain_text") or part.get("text", {}).get("content", "") for part in prop.get("rich_text") or [])
    return ""


def _select_property_name(prop: Any) -> str:
    if not isinstance(prop, dict):
        return ""
    select = prop.get("select") or {}
    if isinstance(select, dict):
        return select.get("name") or ""
    return ""


def _safe_nested_get(mapping: Any, *keys: str) -> Any:
    cur = mapping
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _task_title(item: Dict[str, Any]) -> str:
    title = item.get("title") or ""
    if title:
        return str(title)
    task = item.get("task") or {}
    props = task.get("properties", {}) if isinstance(task, dict) else {}
    for name in ("Task Name", "Name", "Title"):
        text = _plain_text_property(props.get(name, {}))
        if text:
            return text
    return ""


def _metadata_log_headers() -> Optional[Dict[str, str]]:
    token = os.getenv("NOTION_TOKEN", "").strip()
    if not token:
        return None
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }


def _query_ai_processing_log_for_title(title: str, page_size: int = 8) -> List[Dict[str, Any]]:
    if requests is None:
        return []
    database_id = os.getenv("NOTION_AI_LOG_DATABASE_ID", "").strip()
    headers = _metadata_log_headers()
    if not database_id or not headers or not title:
        return []
    title = str(title).strip()
    if not title:
        return []

    payload = {
        "page_size": page_size,
        "filter": {
            "or": [
                {"property": "Name", "title": {"contains": title}},
                {"property": "Original", "rich_text": {"contains": title}},
                {"property": "Final Task", "rich_text": {"contains": title}},
            ]
        },
        "sorts": [{"property": "Run Time", "direction": "descending"}],
    }
    try:
        response = requests.post(
            f"https://api.notion.com/v1/databases/{database_id}/query",
            headers=headers,
            json=payload,
            timeout=20,
        )
        if not response.ok:
            return []
        return response.json().get("results") or []
    except Exception:
        return []


def _parse_importance_from_reason(reason: str) -> Optional[Dict[str, Any]]:
    if not reason:
        return None
    match = re.search(r"-\s*Importance:\s*([^\n(]+)(?:\s*\(([^)]*)\))?", reason)
    if not match:
        return None
    value = match.group(1).strip()
    metadata = match.group(2) or ""
    source = ""
    confidence = None
    source_match = re.search(r"source=([^,\s)]+)", metadata)
    if source_match:
        source = source_match.group(1).strip()
    confidence_match = re.search(r"confidence=([0-9.]+)", metadata)
    if confidence_match:
        try:
            confidence = float(confidence_match.group(1))
        except Exception:
            confidence = confidence_match.group(1)
    return {
        "value": value,
        "source": source or "ai_log_metadata",
        "confidence": confidence,
        "provenance": "ai_log_metadata",
    }


def _created_original_has_marker(entries: List[Dict[str, Any]], markers: Iterable[str]) -> str:
    marker_tuple = tuple(marker.lower() for marker in markers)
    for entry in entries:
        props = entry.get("properties", {}) if isinstance(entry, dict) else {}
        action = _select_property_name(props.get("Action", {})).lower()
        if action and action != "created":
            continue
        original = _plain_text_property(props.get("Original", {}))
        lower = original.lower()
        if any(marker in lower for marker in marker_tuple):
            return original
    return ""


def _extract_metadata_provenance(item: Dict[str, Any], entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    task = item.get("task") or {}
    props = task.get("properties", {}) if isinstance(task, dict) else {}

    current_priority = _safe_nested_get(props, "Priority", "select", "name") or ""
    current_urgency = _safe_nested_get(props, "Urgency", "select", "name") or ""

    provenance = {
        "priority": {"current": current_priority or "unset", "provenance": "manual_or_unknown"},
        "urgency": {"current": current_urgency or "unset", "provenance": "manual_or_unknown"},
        "ai_log_matches": len(entries),
    }

    for entry in entries:
        props = entry.get("properties", {}) if isinstance(entry, dict) else {}
        reason = _plain_text_property(props.get("Reason", {}))
        parsed = _parse_importance_from_reason(reason)
        if parsed:
            provenance["priority"].update(parsed)
            break

    important_original = _created_original_has_marker(entries, ["important", "high importance"])
    if important_original and provenance["priority"].get("provenance") == "manual_or_unknown":
        provenance["priority"].update({
            "provenance": "explicit_marker_from_original",
            "source": "explicit_marker",
            "confidence": 1.0,
        })

    urgent_original = _created_original_has_marker(entries, ["urgent", "asap", "high urgency"])
    if urgent_original:
        provenance["urgency"].update({
            "provenance": "explicit_marker_from_original",
            "source": "explicit_marker",
            "confidence": 1.0,
        })

    return provenance


def _provenance_category(prov: Dict[str, Any]) -> str:
    priority = prov.get("priority", {}) if isinstance(prov, dict) else {}
    urgency = prov.get("urgency", {}) if isinstance(prov, dict) else {}
    sources = {priority.get("source"), urgency.get("source")}
    provenances = {priority.get("provenance"), urgency.get("provenance")}
    if "explicit_marker" in sources:
        return "explicit_marker"
    if "ai_log_metadata" in provenances:
        return "ai_inferred"
    return "manual_or_unknown"


def _build_bna_provenance(winners: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for idx, item in enumerate(winners or [], start=1):
        title = _task_title(item)
        entries = _query_ai_processing_log_for_title(title)
        prov = _extract_metadata_provenance(item, entries)
        category = _provenance_category(prov)
        out.append({
            "rank": idx,
            "title": title,
            "category": category,
            "priority": prov.get("priority", {}),
            "urgency": prov.get("urgency", {}),
            "ai_log_matches": prov.get("ai_log_matches", 0),
        })
    return out


def _ensure_fieldnames(path: Path, fieldnames: List[str]) -> None:
    """Ensure CSV header matches current schema, migrating old rows safely."""
    if not path.exists() or path.stat().st_size == 0:
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
        return

    with path.open("r", newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        existing = reader.fieldnames or []
        rows = list(reader)

    if existing == fieldnames:
        return

    backup = path.with_name(path.stem + f".pre_a1_1_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}" + path.suffix)
    shutil.copy2(path, backup)

    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for old in rows:
            writer.writerow({name: old.get(name, "") for name in fieldnames})


def write_runtime_analytics(
    ranked: List[Dict[str, Any]],
    winners: List[Dict[str, Any]],
    *,
    project_root: str | None = None,
    run_label: str = "runtime",
) -> Dict[str, Any]:
    """Write one run-level analytics row and latest JSON snapshot.

    Read-only local analytics. No Notion mutations, no ranking changes.
    """
    root = Path(project_root or os.getcwd())
    logs_dir = root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    score_bands = _counter_from_score_bands(ranked)
    scoring_sources = _scoring_sources(ranked)
    signal_distribution = _counter_from_reasons(ranked)
    bna_signal_distribution = _counter_from_reasons(winners)
    low_signal_bna_count = sum(
        1
        for item in winners
        if (item.get("score", 0) or 0) <= 3 or (item.get("reasons") or []) == ["baseline_executable"]
    )

    bna_provenance = _build_bna_provenance(winners)
    provenance_mix = Counter(item.get("category", "manual_or_unknown") for item in bna_provenance)

    bna_details = []
    provenance_by_rank = {item.get("rank"): item for item in bna_provenance}
    for idx, item in enumerate(winners, start=1):
        bna_details.append({
            "rank": idx,
            "title": _task_title(item),
            "score": item.get("score", 0),
            "reasons": [str(r) for r in (item.get("reasons") or [])],
            "components": _component_pairs(item),
            "provenance": provenance_by_rank.get(idx, {}),
        })

    analytics = {
        "version": VERSION,
        "run_timestamp_utc": now,
        "run_label": run_label,
        "ranked_count": len(ranked),
        "bna_winner_count": len(winners),
        "score_bands": dict(sorted(score_bands.items())),
        "scoring_sources": dict(sorted(scoring_sources.items())),
        "signal_distribution": dict(sorted(signal_distribution.items())),
        "bna_signal_distribution": dict(sorted(bna_signal_distribution.items())),
        "low_signal_bna_count": low_signal_bna_count,
        "bna_titles": [_task_title(item) for item in winners],
        "bna_details": bna_details,
        "bna_provenance": bna_provenance,
        "bna_provenance_mix": dict(sorted(provenance_mix.items())),
        "bna_explicit_marker_count": provenance_mix.get("explicit_marker", 0),
        "bna_ai_inferred_count": provenance_mix.get("ai_inferred", 0),
        "bna_manual_or_unknown_count": provenance_mix.get("manual_or_unknown", 0),
        "authority_impact": "none",
        "mutations": 0,
        "mode": "read_only_analytics_ledger",
    }

    latest_json = logs_dir / "runtime_analytics_latest.json"
    latest_json.write_text(json.dumps(analytics, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    csv_path = logs_dir / "runtime_analytics.csv"
    fieldnames = [
        "run_timestamp_utc",
        "run_label",
        "ranked_count",
        "bna_winner_count",
        "low_signal_bna_count",
        "bna_explicit_marker_count",
        "bna_ai_inferred_count",
        "bna_manual_or_unknown_count",
        "score_bands_json",
        "scoring_sources_json",
        "signal_distribution_json",
        "bna_signal_distribution_json",
        "bna_provenance_mix_json",
        "bna_provenance_json",
        "bna_titles_json",
        "authority_impact",
        "mutations",
        "mode",
    ]
    _ensure_fieldnames(csv_path, fieldnames)
    row = {
        "run_timestamp_utc": now,
        "run_label": run_label,
        "ranked_count": len(ranked),
        "bna_winner_count": len(winners),
        "low_signal_bna_count": low_signal_bna_count,
        "bna_explicit_marker_count": analytics["bna_explicit_marker_count"],
        "bna_ai_inferred_count": analytics["bna_ai_inferred_count"],
        "bna_manual_or_unknown_count": analytics["bna_manual_or_unknown_count"],
        "score_bands_json": _safe_json(analytics["score_bands"]),
        "scoring_sources_json": _safe_json(analytics["scoring_sources"]),
        "signal_distribution_json": _safe_json(analytics["signal_distribution"]),
        "bna_signal_distribution_json": _safe_json(analytics["bna_signal_distribution"]),
        "bna_provenance_mix_json": _safe_json(analytics["bna_provenance_mix"]),
        "bna_provenance_json": _safe_json(analytics["bna_provenance"]),
        "bna_titles_json": _safe_json(analytics["bna_titles"]),
        "authority_impact": "none",
        "mutations": 0,
        "mode": "read_only_analytics_ledger",
    }
    with csv_path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writerow(row)

    print(f"\n=== {SUMMARY_MARKER} ===")
    print(f"[Runtime Analytics] ledger: {csv_path}")
    print(f"[Runtime Analytics] latest_json: {latest_json}")
    print(
        "[Runtime Analytics] execution: "
        f"ranked={len(ranked)}; winners={len(winners)}; low_signal_bna={low_signal_bna_count}"
    )
    print(
        "[Runtime Analytics] score_bands: "
        + ("; ".join(f"{k}={v}" for k, v in sorted(score_bands.items())) or "none")
    )
    print(
        "[Runtime Analytics] bna_signals: "
        + ("; ".join(f"{k}={v}" for k, v in sorted(bna_signal_distribution.items())) or "none")
    )
    print(
        "[Runtime Analytics] bna_provenance: "
        + ("; ".join(f"{k}={v}" for k, v in sorted(provenance_mix.items())) or "none")
    )
    print("[Runtime Analytics] authority_impact=none; mutations=0; mode=read_only_analytics_ledger")

    return analytics
